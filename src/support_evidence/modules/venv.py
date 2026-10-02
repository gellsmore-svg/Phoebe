"""Bounded POSIX venv metadata inspection. Never execute target interpreters,
activation scripts, .pth hooks, pip, imports or entry points. PASS is static only.
"""
import hashlib
import errno
import os
import re
import stat
from email.parser import BytesParser
from pathlib import Path
from packaging.requirements import Requirement, InvalidRequirement
from packaging.specifiers import SpecifierSet, InvalidSpecifier
from packaging.utils import canonicalize_name
from packaging.version import Version, InvalidVersion
from .common import CollectionStatus, validate_local_probe

OPERATIONS = {"venv_layout", "venv_isolation", "venv_dependencies", "venv_scripts"}
BUDGET = 4*1024*1024

class Tree:
    def __init__(self, path):
        self.fd = os.open(path, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        self.used = 0
    def close(self): os.close(self.fd)
    def open(self, relative, directory=False):
        fd = os.dup(self.fd)
        try:
            parts = relative.split("/")
            if any(p in {"", ".", ".."} for p in parts): raise ValueError("invalid relative path")
            for i, part in enumerate(parts):
                last = i == len(parts)-1
                flags = os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK
                if not last or directory: flags |= os.O_DIRECTORY
                new = os.open(part, flags, dir_fd=fd); os.close(fd); fd = new
            return fd
        except BaseException:
            os.close(fd); raise
    def read(self, relative, limit=262144):
        fd = self.open(relative)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode): raise CollectionStatus("ERROR", "venv_metadata_not_regular")
            with os.fdopen(os.dup(fd), "rb") as stream: raw = stream.read(limit+1)
            self.used += len(raw)
            if len(raw)>limit or self.used>BUDGET: raise CollectionStatus("ERROR", "venv_metadata_budget")
            after = os.fstat(fd)
            if (before.st_size,before.st_mtime_ns,before.st_ctime_ns) != (after.st_size,after.st_mtime_ns,after.st_ctime_ns):
                raise CollectionStatus("UNAVAILABLE", "venv_metadata_changed")
            return raw
        finally: os.close(fd)
    def names(self, relative):
        fd = self.open(relative, directory=True)
        try:
            names=[]
            with os.scandir(fd) as items:
                for item in items:
                    names.append(item.name)
                    if len(names)>4096: raise CollectionStatus("ERROR", "venv_metadata_budget")
            return sorted(names)
        finally: os.close(fd)

def configuration(raw):
    try:
        text = raw.decode("utf-8"); cfg={}
        for line in text.splitlines():
            if not line.strip(): continue
            key, value = line.split("=",1); key=key.strip().lower()
            if key in cfg: raise ValueError()
            cfg[key]=value.strip()
        if not re.fullmatch(r"3\.[0-9]{1,2}\.[0-9]{1,3}", cfg.get("version","")): raise ValueError()
        if cfg.get("include-system-site-packages") not in {"true","false"}: raise ValueError()
        if not Path(cfg.get("home", "")).is_absolute(): raise ValueError()
    except (ValueError, UnicodeError): raise CollectionStatus("ERROR", "venv_configuration_malformed") from None
    return cfg

def layout(tree, path, cfg, manifest, expected):
    from ..policy import allowed_path
    actual = cfg["version"]
    if not (actual == expected["python_version"] or actual.startswith(expected["python_version"]+".")):
        return {"reason":"venv_version_mismatch"}, False
    home = Path(cfg["home"])
    # External base installation and symlink destinations require explicit approval.
    if str(home.resolve()) not in manifest.get("allowed_paths",[]): raise PermissionError()
    if not home.is_dir(): return {"reason":"venv_base_missing"}, False
    executable = path/"bin"/"python"
    # Pin bin directory before stat; only the interpreter symlink may leave root.
    try: fd = tree.open("bin", directory=True)
    except FileNotFoundError: return {"reason":"venv_interpreter_missing"}, False
    try:
        link = os.readlink("python", dir_fd=fd) if stat.S_ISLNK(os.stat("python",dir_fd=fd,follow_symlinks=False).st_mode) else None
        if link is not None:
            resolved = (path/"bin"/link).resolve()
            if str(resolved) not in manifest.get("allowed_paths",[]): raise PermissionError()
            info = resolved.stat()
            valid = stat.S_ISREG(info.st_mode) and os.access(resolved,os.X_OK)
        else:
            info = os.stat("python",dir_fd=fd,follow_symlinks=False)
            valid = stat.S_ISREG(info.st_mode) and bool(info.st_mode & 0o111)
    except FileNotFoundError: return {"reason":"venv_interpreter_missing"}, False
    finally: os.close(fd)
    if not valid: return {"reason":"venv_interpreter_unusable"}, False
    major,minor,patch=map(int,actual.split("."))
    return {"python_version_num":major*10000+minor*100+patch, "interpreter_present":True}, True

def marker_matches(requirement, version, extras):
    if requirement.marker is None: return True
    text = str(requirement.marker)
    if "extra" in text and re.search(r'\bextra\s*(?:!=|not in|in|<=|>=|<|>)',text):
        raise CollectionStatus("UNAVAILABLE", "venv_marker_environment_unknown")
    # Never substitute the collector's platform or implementation for the target.
    if re.search(r"\b(os_name|sys_platform|platform_machine|platform_release|platform_system|platform_version|platform_python_implementation|implementation_name|implementation_version)\b",text):
        raise CollectionStatus("UNAVAILABLE", "venv_marker_environment_unknown")
    env={"python_version":".".join(version.split(".")[:2]),"python_full_version":version}
    return any(requirement.marker.evaluate(dict(env,extra=extra)) for extra in {"",*extras})

def dependencies(tree, cfg, expected):
    version=cfg["version"]; minor=".".join(version.split(".")[:2])
    site="lib/python"+minor+"/site-packages"
    try: names=tree.names(site)
    except FileNotFoundError: return {"reason":"venv_site_packages_missing"}, False
    ambiguous = any(n.endswith((".pth",".egg-info",".egg-link")) for n in names)
    directories=[n for n in names if n.endswith(".dist-info")]
    if len(directories)>512: raise CollectionStatus("ERROR", "venv_metadata_budget")
    installed={}; metadata=[]
    for directory in directories:
        raw=tree.read(site+"/"+directory+"/METADATA")
        msg=BytesParser().parsebytes(raw,headersonly=True)
        if msg.defects or any(len(msg.get_all(k,[]))!=1 for k in ["Metadata-Version","Name","Version"]):
            raise CollectionStatus("ERROR", "venv_metadata_malformed")
        if msg["Metadata-Version"] not in {"1.0","1.1","1.2","2.0","2.1","2.2","2.3","2.4","2.5"}:
            raise CollectionStatus("UNAVAILABLE", "venv_metadata_version_unknown")
        name=msg["Name"]
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,199}",name): raise CollectionStatus("ERROR", "venv_metadata_malformed")
        name=canonicalize_name(name)
        if name in installed: raise CollectionStatus("UNAVAILABLE", "venv_duplicate_distribution")
        try: parsed=Version(msg["Version"])
        except InvalidVersion: raise CollectionStatus("ERROR", "venv_metadata_malformed") from None
        installed[name]=(parsed,msg); metadata.append((site+"/"+directory+"/METADATA",hashlib.sha256(raw).digest()))
    missing=set(); conflicts=set(); unknown=ambiguous; extras={n:set() for n in installed}; visited={}; queue=list(installed)
    def check(text, source, selected_extras):
        nonlocal unknown
        if len(text)>512: raise CollectionStatus("ERROR", "venv_metadata_budget")
        try: req=Requirement(text)
        except InvalidRequirement: raise CollectionStatus("ERROR", "venv_metadata_malformed") from None
        if req.url: unknown=True; return
        try: active=marker_matches(req,version,selected_extras)
        except CollectionStatus: unknown=True; return
        if not active: return
        name=canonicalize_name(req.name)
        if name not in installed: missing.add((source,str(req))); return
        if installed[name][0] not in req.specifier: conflicts.add((source,str(req)))
        provided={canonicalize_name(e) for e in installed[name][1].get_all("Provides-Extra",[])}
        requested={canonicalize_name(e) for e in req.extras}
        if requested-provided: unknown=True
        if not requested <= extras[name]: extras[name].update(requested); queue.append(name)
    for text in expected["requirements"]: check(text,"contract",set())
    steps=0
    while queue:
        name=queue.pop(); selected=frozenset(extras[name])
        if visited.get(name)==selected: continue
        visited[name]=selected; steps+=1
        if steps>2048: raise CollectionStatus("ERROR", "venv_metadata_budget")
        _, msg=installed[name]
        try:
            python_specs=msg.get_all("Requires-Python",[])
            if len(python_specs)>1: raise InvalidSpecifier()
            if python_specs and Version(version) not in SpecifierSet(python_specs[0]): conflicts.add((name,"python"))
        except (InvalidSpecifier,InvalidVersion): raise CollectionStatus("ERROR", "venv_metadata_malformed") from None
        requirements=msg.get_all("Requires-Dist",[])
        if len(requirements)>256: raise CollectionStatus("ERROR", "venv_metadata_budget")
        for text in requirements: check(text,name,selected)
    if tree.names(site) != names: raise CollectionStatus("UNAVAILABLE", "venv_metadata_changed")
    for relative, signature in metadata:
        if hashlib.sha256(tree.read(relative)).digest() != signature: raise CollectionStatus("UNAVAILABLE", "venv_metadata_changed")
    value={"distributions":len(installed),"missing_dependencies":len(missing),"dependency_conflicts":len(conflicts),"metadata_complete":not unknown}
    if missing: return dict(value,reason="venv_dependencies_missing"), False
    if conflicts: return dict(value,reason="venv_dependency_conflict"), False
    if unknown: raise CollectionStatus("UNAVAILABLE", "venv_dependency_scope_unknown", **value)
    return value, True


def scripts(tree, path):
    try: names=tree.names("bin")
    except FileNotFoundError: return {"reason":"venv_interpreter_missing"},False
    checked=stale=0; unknown=False
    if len(names)>256: raise CollectionStatus("ERROR", "venv_metadata_budget")
    for name in names:
        if re.fullmatch(r"python[0-9.]*",name): continue
        try: fd=tree.open("bin/"+name)
        except OSError as error:
            if error.errno in {errno.ELOOP,errno.ENOTDIR}: unknown=True; continue
            raise
        try:
            info=os.fstat(fd)
            if not stat.S_ISREG(info.st_mode): unknown=True; continue
            prefix=os.read(fd,4096)
            if not prefix.startswith(b"#!"): continue
            line=prefix.split(b"\n",1)[0].decode("utf-8",errors="strict")[2:].strip()
            executable=line.split()[0]
            if re.fullmatch(r"python[0-9.]*",Path(executable).name):
                checked+=1
                if not Path(executable).is_absolute() or Path(executable).parent != path/"bin": stale+=1
            elif Path(executable).name in {"env","sh","bash"}: unknown=True
        except (UnicodeError,IndexError): unknown=True
        finally: os.close(fd)
    value={"python_scripts":checked,"stale_script_paths":stale}
    if stale: return dict(value,reason="venv_script_path_mismatch"),False
    if unknown or checked==0: raise CollectionStatus("UNAVAILABLE", "venv_script_scope_unknown",**value)
    return value,True

def collect(probe, manifest):
    validate_local_probe(probe,manifest)
    from ..policy import allowed_path
    path = allowed_path(probe["target"],manifest).resolve()
    if os.name != "posix": raise CollectionStatus("UNAVAILABLE", "venv_platform_unsupported")
    try: tree=Tree(path)
    except FileNotFoundError: return {"reason":"venv_missing"}, False
    except NotADirectoryError: return {"reason":"venv_root_not_directory"}, False
    except PermissionError: raise CollectionStatus("DENIED", "venv_metadata_permission") from None
    try:
        try: raw=tree.read("pyvenv.cfg",16384)
        except FileNotFoundError: return {"reason":"venv_configuration_missing"}, False
        cfg=configuration(raw)
        if not 11 <= int(cfg["version"].split(".")[1]) <= 14:
            raise CollectionStatus("UNAVAILABLE", "venv_version_unsupported")
        if probe["operation"] == "venv_layout": result=layout(tree,path,cfg,manifest,probe["expected"])
        elif probe["operation"] == "venv_isolation":
            isolated=cfg["include-system-site-packages"]=="false"
            value={"system_site_packages":not isolated}
            result=(value,True) if isolated==probe["expected"]["isolated"] else (dict(value,reason="venv_isolation_mismatch"),False)
        elif probe["operation"] == "venv_scripts": result=scripts(tree,path)
        else:
            if cfg["include-system-site-packages"]=="true": raise CollectionStatus("UNAVAILABLE", "venv_system_packages_unmeasured")
            result=dependencies(tree,cfg,probe["expected"])
        if tree.read("pyvenv.cfg",16384)!=raw: raise CollectionStatus("UNAVAILABLE", "venv_metadata_changed")
        info=os.stat(path,follow_symlinks=False); opened=os.fstat(tree.fd)
        if (info.st_dev,info.st_ino)!=(opened.st_dev,opened.st_ino): raise CollectionStatus("UNAVAILABLE", "venv_metadata_changed")
        return result
    except PermissionError: raise CollectionStatus("DENIED", "venv_metadata_permission") from None
    except OSError as error:
        if error.errno in {errno.ELOOP,errno.ENOTDIR}: raise CollectionStatus("UNAVAILABLE", "venv_metadata_unsafe_path") from None
        if isinstance(error,FileNotFoundError): raise CollectionStatus("UNAVAILABLE", "venv_metadata_missing") from None
        raise
    finally: tree.close()
