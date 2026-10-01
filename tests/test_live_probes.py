import copy
import datetime
import http.server
import ipaddress
import json
import socket
import ssl
import threading
import time
from contextlib import contextmanager
from pathlib import Path
import pytest
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from support_evidence.supervisor import run_probe
from support_evidence.policy import validate_manifest

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
        if self.path=="/redirect":
            self.send_response(302);self.send_header("Location","http://169.254.169.254/latest/meta-data/");self.end_headers();return
        self.send_response(200);self.end_headers()
        self.wfile.write(json.dumps({"ok":self.path!="/wrong"}).encode())

@contextmanager
def http_fixture():
    server=http.server.ThreadingHTTPServer(("127.0.0.1",0),Handler)
    t=threading.Thread(target=server.serve_forever,daemon=True);t.start()
    try:yield server.server_address[1]
    finally:server.shutdown();server.server_close();t.join()

@pytest.mark.parametrize("path,expected",[("/correct","PASS"),("/wrong","FAIL"),("/redirect","FAIL")])
def test_real_http_oracle_and_redirect(probe,manifest,path,expected):
    with http_fixture() as port:
        p=copy.deepcopy(probe);p.update(target=f"http://127.0.0.1:{port}{path}",route=path);p["expected"]={"status":200,"json_key":"ok","json_value":True}
        m=copy.deepcopy(manifest);m["allowed_targets"]=[p["target"]];m["probes"]=[p]
        r=run_probe(p,validate_manifest(m));assert r["predicate_status"]==expected and r["collector_status"]=="OK"
        assert "body" not in r["value"]

def test_real_tcp_connection_refused(probe,manifest):
    with socket.socket() as s:s.bind(("127.0.0.1",0));port=s.getsockname()[1]
    p=copy.deepcopy(probe);p.update(operation="tcp",target=f"tcp://127.0.0.1:{port}")
    m=copy.deepcopy(manifest);m["allowed_targets"]=[p["target"]];m["probes"]=[p]
    r=run_probe(p,m);assert r["predicate_status"]=="FAIL" and r["collector_status"]=="OK"

def make_cert(directory,expired=False,mismatch=False):
    now=datetime.datetime.now(datetime.timezone.utc);key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,"fixture CA")])
    ca=x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-datetime.timedelta(days=10)).not_valid_after(now+datetime.timedelta(days=10)).add_extension(x509.BasicConstraints(ca=True,path_length=None),critical=True).sign(key,hashes.SHA256())
    leafkey=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    leaf=x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,"fixture")])).issuer_name(name).public_key(leafkey.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-datetime.timedelta(days=2)).not_valid_after(now-datetime.timedelta(days=1) if expired else now+datetime.timedelta(days=2)).add_extension(x509.SubjectAlternativeName([x509.DNSName("wrong.example") if mismatch else x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]),critical=False).sign(key,hashes.SHA256())
    ca_path=directory/"ca.pem";cert_path=directory/"leaf.pem";key_path=directory/"leaf.key"
    ca_path.write_bytes(ca.public_bytes(serialization.Encoding.PEM));cert_path.write_bytes(leaf.public_bytes(serialization.Encoding.PEM));key_path.write_bytes(leafkey.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
    return ca_path,cert_path,key_path

@pytest.mark.parametrize("expired,mismatch,reason",[(False,False,None),(True,False,"tls_expired"),(False,True,"tls_hostname_mismatch")])
def test_real_tls_valid_expired_and_mismatch(tmp_path,probe,manifest,monkeypatch,expired,mismatch,reason):
    ca,cert,key=make_cert(tmp_path,expired,mismatch)
    context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.load_cert_chain(cert,key)
    listener=socket.socket();listener.bind(("127.0.0.1",0));listener.listen(1);port=listener.getsockname()[1]
    def serve():
        try:
            conn,_=listener.accept()
            with conn:
                try:
                    with context.wrap_socket(conn,server_side=True):pass
                except ssl.SSLError:pass
        finally:listener.close()
    thread=threading.Thread(target=serve,daemon=True);thread.start();monkeypatch.setenv("SSL_CERT_FILE",str(ca))
    p=copy.deepcopy(probe);p.update(operation="tls",target=f"tls://127.0.0.1:{port}");p["expected"]={"min_valid_days":0}
    m=copy.deepcopy(manifest);m["allowed_targets"]=[p["target"]];m["probes"]=[p]
    r=run_probe(p,m);thread.join(timeout=3)
    assert r["collector_status"]=="OK"
    assert r["predicate_status"]==("FAIL" if reason else "PASS")
    if reason:assert r["value"]["reason"]==reason

def test_real_unix_socket_absent(probe,manifest,tmp_path):
    path=str(tmp_path/"not-listening.sock")
    p=copy.deepcopy(probe);p.update(operation="unix",target=path)
    m=copy.deepcopy(manifest);m["allowed_targets"]=[path];m["allowed_paths"]=[path];m["probes"]=[p]
    r=run_probe(p,m)
    # File absence is target-operation failure for a UNIX connection, not collection absence.
    assert r["predicate_status"]=="FAIL"
