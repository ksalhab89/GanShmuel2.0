from dataclasses import dataclass
from typing import Optional, List, Union


@dataclass
class Provider:
    id: int
    name: str


@dataclass
class Rate:
    product_id: str
    rate: int
    scope: str


@dataclass
class Truck:
    id: str
    provider_id: int


@dataclass
class WeightTransaction:
    """Weight service transaction model."""
    id: str
    direction: str
    bruto: Optional[int]
    neto: Optional[Union[int, str]]  # Can be "na"
    produce: Optional[str]
    truck: Optional[str]
    containers: List[str]
    timestamp: Optional[str]


@dataclass
class WeightItem:
    """Weight service item details model."""
    id: str
    tara: Union[int, str]  # Can be "na"
    sessions: List[str]