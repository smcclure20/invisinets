from typing import Union, Optional, TypeVar, Type
from abc import ABC, abstractmethod


class Resource(ABC):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @abstractmethod
    def terminate(self):
        return NotImplemented


class EndpointIP(Resource):
    @property
    @abstractmethod
    def name(self) -> str:
        return NotImplemented

    @property
    @abstractmethod
    def subnet_id(self) -> str:
        return NotImplemented

    @property
    @abstractmethod
    def endpoint_id(self) -> str:
        return NotImplemented

    @property
    @abstractmethod
    def public_ip(self) -> str:
        return NotImplemented

    @property
    @abstractmethod
    def private_ip(self) -> str:
        return NotImplemented


class ServiceIP(Resource):
    @property
    @abstractmethod
    def name(self) -> str:
        return NotImplemented

    @property
    @abstractmethod
    def subnet_id(self) -> str:
        return NotImplemented

    @property
    @abstractmethod
    def endpoint_id(self) -> str:
        return NotImplemented


TInvisinet = TypeVar('TInvisinet', bound='Invisinet')


class Invisinet(ABC):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @staticmethod
    @abstractmethod
    def list_deployments() -> [TInvisinet]:
        return NotImplemented

    @property
    @abstractmethod
    def deployment_id(self) -> str:
        return NotImplemented

    @abstractmethod
    def request_eip(self, name: Optional[str], use_existing_vm_id: Optional[str] = None) -> EndpointIP:
        return NotImplemented

    @property
    @abstractmethod
    def active_eip(self) -> [EndpointIP]:
        return NotImplemented

    @abstractmethod
    def request_sip(self, name: Optional[str]) -> ServiceIP:
        return NotImplemented

    @property
    @abstractmethod
    def active_sip(self) -> [ServiceIP]:
        return NotImplemented

    @abstractmethod
    def bind(self, sip: ServiceIP, eip: EndpointIP):
        return NotImplemented

    @abstractmethod
    def annotate(self,
                 endpoints: (EndpointIP, EndpointIP),
                 middlebox: EndpointIP):
        return NotImplemented

