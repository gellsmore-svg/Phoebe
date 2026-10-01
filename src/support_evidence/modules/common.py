"""A missing diagnostic prerequisite does not fail a service contract."""
class CollectionStatus(Exception):
    def __init__(self, collector, reason, **metadata):
        self.collector = collector
        self.value = {"reason": reason, **metadata}
