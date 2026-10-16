"""
Case State Manager
Tracks case lifecycle and prevents stale results from being displayed.
"""

import json
import uuid
from enum import Enum
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict
from dataclasses import dataclass, asdict

class CaseState(Enum):
    """Case processing states"""
    RECEIVED = "received"
    VALIDATED = "validated"
    INFERENCE = "inference"
    RESULTS_READY = "results_ready"
    FAILED = "failed"

@dataclass
class CaseMetadata:
    """Metadata for a case"""
    case_id: str
    state: CaseState
    created_at: str
    updated_at: str
    modality_files: Dict[str, str]  # modality -> filename
    error_message: Optional[str] = None
    sha256_hashes: Optional[Dict[str, str]] = None
    shape: Optional[tuple] = None
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['state'] = self.state.value
        return data
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create from dictionary"""
        data['state'] = CaseState(data['state'])
        return cls(**data)

class CaseStateManager:
    """Manages case state and prevents stale results"""
    
    def __init__(self, data_root: Path):
        self.data_root = Path(data_root)
        self.cases_dir = self.data_root / "cases"
        self.cases_dir.mkdir(parents=True, exist_ok=True)
    
    def create_case(self, modality_files: Dict[str, str]) -> str:
        """
        Create new case with unique ID.
        
        Returns:
            case_id: Unique identifier for this case
        """
        case_id = str(uuid.uuid4())
        
        # Create case directory
        case_dir = self.cases_dir / case_id
        case_dir.mkdir(parents=True, exist_ok=True)
        
        # Create metadata
        now = datetime.utcnow().isoformat()
        metadata = CaseMetadata(
            case_id=case_id,
            state=CaseState.RECEIVED,
            created_at=now,
            updated_at=now,
            modality_files=modality_files
        )
        
        self._save_metadata(case_id, metadata)
        return case_id
    
    def update_state(
        self, 
        case_id: str, 
        new_state: CaseState,
        error_message: Optional[str] = None,
        **kwargs
    ):
        """Update case state and metadata"""
        metadata = self._load_metadata(case_id)
        if metadata is None:
            raise ValueError(f"Case {case_id} not found")
        
        metadata.state = new_state
        metadata.updated_at = datetime.utcnow().isoformat()
        
        if error_message:
            metadata.error_message = error_message
        
        # Update additional fields
        for key, value in kwargs.items():
            if hasattr(metadata, key):
                setattr(metadata, key, value)
        
        self._save_metadata(case_id, metadata)
    
    def get_case_state(self, case_id: str) -> Optional[CaseState]:
        """Get current state of a case"""
        metadata = self._load_metadata(case_id)
        return metadata.state if metadata else None
    
    def get_case_metadata(self, case_id: str) -> Optional[CaseMetadata]:
        """Get complete metadata for a case"""
        return self._load_metadata(case_id)
    
    def can_show_results(self, case_id: str) -> bool:
        """
        Check if results can be displayed for this case.
        Prevents showing stale results from previous cases.
        """
        metadata = self._load_metadata(case_id)
        if metadata is None:
            return False
        
        return metadata.state == CaseState.RESULTS_READY
    
    def get_case_dir(self, case_id: str) -> Path:
        """Get directory for case data"""
        return self.cases_dir / case_id
    
    def _save_metadata(self, case_id: str, metadata: CaseMetadata):
        """Save metadata to disk"""
        metadata_path = self.get_case_dir(case_id) / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata.to_dict(), f, indent=2)
    
    def _load_metadata(self, case_id: str) -> Optional[CaseMetadata]:
        """Load metadata from disk"""
        metadata_path = self.get_case_dir(case_id) / "metadata.json"
        if not metadata_path.exists():
            return None
        
        with open(metadata_path, 'r') as f:
            data = json.load(f)
        
        return CaseMetadata.from_dict(data)
    
    def cleanup_old_cases(self, max_age_hours: int = 24):
        """
        Clean up cases older than max_age_hours.
        This implements the 24-hour deletion requirement.
        """
        import shutil
        from datetime import timedelta
        
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        deleted_count = 0
        
        for case_dir in self.cases_dir.iterdir():
            if not case_dir.is_dir():
                continue
            
            metadata = self._load_metadata(case_dir.name)
            if metadata is None:
                continue
            
            created_at = datetime.fromisoformat(metadata.created_at)
            if created_at < cutoff:
                # Delete entire case directory
                shutil.rmtree(case_dir)
                deleted_count += 1
        
        return deleted_count
