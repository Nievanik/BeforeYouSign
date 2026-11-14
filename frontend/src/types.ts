// Mirrors backend/app/models.py (docs/data-schema.md). Change both in the same commit.

export interface BusinessBrief {
  businessType: string
  city: 'Houston' | 'Los Angeles'
  maxRentMonthly: number
  sizeSqftMin: number | null
  sizeSqftMax: number | null
  parkingRequired: boolean
  mustHaves: string[]
}

export interface Aerial {
  parcelWkt: string
  visibilityScore: number | null
  visibilityReason: string | null
  roadAccessScore: number | null
  roadAccessReason: string | null
  collection: string | null
  parkingSeen: number | null // from parking rows in one photo; null = count unclear; display only, not in the odds
  imageUrl: string
  obliqueDirections: string[] // angled photos at /api/sites/{id}/oblique/{dir}.jpg
}

export interface Room {
  label: string
  areaSqft: number
  widthFt: number
  depthFt: number
}

export interface Interior {
  floorAreaSqft: number
  rooms: Room[]
  estSeats: number
  tourUrl: string
  summary: string | null
}

export interface Competitor {
  name: string
  kind: 'competitor' | 'complement' | 'neutral'
  lat: number
  lon: number
  distanceMi: number
  rating: number | null
  reviewCount: number | null
  isNew: boolean
  attractiveness: number
  address: string | null
  source: 'yelp' | 'osm'
}

export interface Demographics {
  population: number
  medianIncome: number | null
  medianAge: number | null
  tract: string
  densityPerSqMi: number | null
  driveShare: number | null
  walkTransitShare: number | null
  noVehicleShare: number | null
}

export interface Band {
  p10: number
  p50: number
  p90: number
}

export interface MonthBand extends Band {
  month: number
}

export interface RiskFactor {
  factor: string
  impact: number
  text: string
}

export interface SimResult {
  pProfitableBy12: number
  medianMonthProfitable: number | null
  profitM12: Band
  monthlyBands: MonthBand[]
  expectedCustomers: number
  breakEvenCustomers: number
  rentShare: number
  paybackMonths: number | null
  peopleNearby: { residents: number; workers: number }
  riskFactors: RiskFactor[]
  assumptions: Record<string, unknown>
  seed: number
}

export interface Site {
  id: string
  listingId: number
  propertyId: number
  address: string
  lat: number
  lon: number
  sizeSqft: number
  rentMonthly: number | null
  rentPsfYear: number | null
  serviceType: string
  spaceUse: string
  parkingAvailable: boolean | null // CoStar property record; null = not recorded
  parkingSpaces: number | null
  parkingTypes: string[]
  buildingClass: string | null
  yearBuilt: number | null
  photoUrl: string | null
  matterportModelId: string | null
  aerial: Aerial | null
  interior: Interior | null
  competitors: Competitor[]
  demographics: Demographics | null
  sim: SimResult | null
  gaps: string[]
}

export interface RunResult {
  runId: string
  brief: BusinessBrief
  sites: Site[]
  report: string
  createdAt: string
}
