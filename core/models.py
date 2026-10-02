from dataclasses import dataclass, field

MAX_SATURATION_FLOW = 2400
MIN_LOST_TIME = 1
MAX_LOST_TIME = 12
MAX_VOLUME = 5000
CYCLE_STEP = 5
PRACTICAL_CYCLE_LIMIT = 150
MIN_GREEN_WARNING = 5


@dataclass(frozen=True)
class PhaseDef:
    code: str
    label: str
    hint: str


@dataclass(frozen=True)
class PhaseModel:
    key: str
    name: str
    description: str
    phases: tuple[PhaseDef, ...]

    @property
    def phase_count(self) -> int:
        return len(self.phases)


def _phase(code: str, label: str, hint: str = "Vehicles per hour") -> PhaseDef:
    return PhaseDef(code, label, hint)


MODELS: dict[str, PhaseModel] = {
    "2": PhaseModel(
        key="2",
        name="2-Phase",
        description="Standard 4-way or simple T",
        phases=(
            _phase("NS", "North-South Thru and Right"),
            _phase("EW", "East-West Thru and Right"),
        ),
    ),
    "3": PhaseModel(
        key="3",
        name="3-Phase",
        description="T-intersection with major left turn",
        phases=(
            _phase("MajThru", "Major Street Thru and Right"),
            _phase("MajLeft", "Major Street Protected Left"),
            _phase("MinStem", "Minor Street (Stem) All Movements"),
        ),
    ),
    "4": PhaseModel(
        key="4",
        name="4-Phase",
        description="Protected lefts or split phasing",
        phases=(
            _phase("NSL", "NS Protected Left"),
            _phase("NST", "NS Thru and Right"),
            _phase("EWL", "EW Protected Left"),
            _phase("EWT", "EW Thru and Right"),
        ),
    ),
    "6": PhaseModel(
        key="6",
        name="6-Phase",
        description="Major arterial with protected lefts",
        phases=(
            _phase("NBL", "Arterial NB Protected Left"),
            _phase("SBL", "Arterial SB Protected Left"),
            _phase("ArtThru", "Arterial NB and SB Thru and Right"),
            _phase("MinEB", "Minor EB All Movements"),
            _phase("MinWB", "Minor WB All Movements"),
        ),
    ),
    "8": PhaseModel(
        key="8",
        name="8-Phase",
        description="NEMA dual-ring, complex 4-way",
        phases=(
            _phase("NBL", "Northbound Protected Left"),
            _phase("NBT", "Northbound Thru and Right"),
            _phase("SBL", "Southbound Protected Left"),
            _phase("SBT", "Southbound Thru and Right"),
            _phase("EBL", "Eastbound Protected Left"),
            _phase("EBT", "Eastbound Thru and Right"),
            _phase("WBL", "Westbound Protected Left"),
            _phase("WBT", "Westbound Thru and Right"),
        ),
    ),
}


@dataclass
class TimingInput:
    model_key: str
    saturation_flow: float
    lost_time: int
    # demand in veh/hr, keyed by phase code
    volumes: dict[str, float]


@dataclass
class PhaseResult:
    code: str
    label: str
    volume: float
    flow_ratio: float
    green: int
    # this phase's slice of the effective green (green / Te)
    green_share: float


@dataclass
class TimingResult:
    model: PhaseModel
    oversaturated: bool
    total_flow_ratio: float
    total_lost_time: int
    active_count: int
    raw_cycle: float | None = None
    cycle: int | None = None
    effective_green: int | None = None
    # active phases only, in model order
    phases: list[PhaseResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    # only filled when oversaturated
    message: str = ""
