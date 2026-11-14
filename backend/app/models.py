"""Shared contract (docs/data-schema.md). Mirror every change in frontend/src/types.ts.

Fields are camelCase so the JSON matches the docs and the frontend without aliases.
"""
from typing import Literal, Optional

from pydantic import BaseModel


class BusinessBrief(BaseModel):
    businessType: str
    city: Literal["Houston", "Los Angeles"]
    maxRentMonthly: float
    sizeSqftMin: Optional[float] = None
    sizeSqftMax: Optional[float] = None
    mustHaves: list[str] = []


class Aerial(BaseModel):
    parcelWkt: str
    visibilityScore: Optional[int] = None  # 1-5, null until vision has run
    visibilityReason: Optional[str] = None
    roadAccessScore: Optional[int] = None  # 1-5
    roadAccessReason: Optional[str] = None
    collection: Optional[str] = None
    parkingSeen: Optional[int] = None  # from parking rows detected on the parcel in one photo; null = count unclear (areas still outlined); display only
    imageUrl: str
    obliqueDirections: list[str] = []  # "north"/"east"/"south"/"west": angled photos at /api/sites/{id}/oblique/{dir}.jpg


class Room(BaseModel):
    label: str
    areaSqft: float
    widthFt: float
    depthFt: float


class Interior(BaseModel):
    floorAreaSqft: float
    rooms: list[Room] = []
    estSeats: int
    tourUrl: str


class Competitor(BaseModel):
    name: str
    kind: Literal["competitor", "complement", "neutral"]
    lat: float
    lon: float
    distanceMi: float
    rating: Optional[float] = None
    reviewCount: Optional[int] = None
    isNew: bool = False
    attractiveness: float
    source: Literal["yelp", "osm"]


class Demographics(BaseModel):
    population: int
    medianIncome: Optional[float] = None
    medianAge: Optional[float] = None
    tract: str
    densityPerSqMi: Optional[float] = None
    driveShare: Optional[float] = None  # 0-1, commuters who go by car (proxy for how customers arrive)
    walkTransitShare: Optional[float] = None  # 0-1, commuters who walk or take transit
    noVehicleShare: Optional[float] = None  # 0-1, households without a car


class Band(BaseModel):
    p10: float
    p50: float
    p90: float


class MonthBand(Band):
    month: int


class PeopleNearby(BaseModel):
    residents: float
    workers: float


class RiskFactor(BaseModel):
    factor: str
    impact: float
    text: str


class SimResult(BaseModel):
    pProfitableBy12: float  # 0-1, headline
    medianMonthProfitable: Optional[int] = None
    profitM12: Band
    monthlyBands: list[MonthBand]
    expectedCustomers: float
    breakEvenCustomers: float
    rentShare: float
    paybackMonths: Optional[int] = None
    peopleNearby: PeopleNearby
    riskFactors: list[RiskFactor]
    assumptions: dict
    seed: int


class Site(BaseModel):
    id: str
    listingId: int
    propertyId: int
    address: str
    lat: float
    lon: float
    sizeSqft: float
    rentMonthly: Optional[float] = None
    rentPsfYear: Optional[float] = None
    serviceType: str
    spaceUse: str
    photoUrl: Optional[str] = None
    matterportModelId: Optional[str] = None
    aerial: Optional[Aerial] = None
    interior: Optional[Interior] = None
    competitors: list[Competitor] = []
    demographics: Optional[Demographics] = None
    sim: Optional[SimResult] = None
    gaps: list[str] = []


class RunResult(BaseModel):
    runId: str
    brief: BusinessBrief
    sites: list[Site]  # ranked by sim.pProfitableBy12
    report: str  # markdown
    createdAt: str  # ISO 8601
