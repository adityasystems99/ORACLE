"""Thread-safe file-based JSON persistence for ORACLE entities."""

import json
import logging
from pathlib import Path
from threading import RLock
from typing import Any, Dict, List, Optional, Type, TypeVar
from pydantic import BaseModel

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class DiskStore:
    """Manages disk-backed JSON collections with atomic writes and schema hydration."""

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

    def _get_path(self, collection_name: str) -> Path:
        return self.data_dir / f"{collection_name}.json"

    def save_all(self, collection_name: str, items: List[BaseModel]) -> None:
        """Atomically persist a list of Pydantic models to disk as JSON."""
        target_path = self._get_path(collection_name)
        temp_path = self.data_dir / f"{collection_name}.tmp"
        
        data = [item.model_dump(mode="json") for item in items]
        with self._lock:
            try:
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                temp_path.replace(target_path)
            except Exception as e:
                logger.error(f"Failed to persist collection {collection_name}: {e}")
                if temp_path.exists():
                    temp_path.unlink()
                raise

    def load_all(self, collection_name: str, model_cls: Type[T]) -> List[T]:
        """Load and hydrate all items from a collection JSON file."""
        target_path = self._get_path(collection_name)
        if not target_path.exists():
            return []
        with self._lock:
            try:
                with open(target_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, list):
                    logger.warning(f"Expected list in {target_path}, got {type(data)}")
                    return []
                return [model_cls.model_validate(item) for item in data]
            except Exception as e:
                logger.error(f"Error loading collection {collection_name}: {e}")
                return []

    def upsert_item(self, collection_name: str, item: T, id_field: str = "id") -> None:
        """Upsert a single item into the collection."""
        with self._lock:
            items = self.load_all(collection_name, type(item))
            item_id = getattr(item, id_field)
            updated = False
            for idx, existing in enumerate(items):
                if getattr(existing, id_field) == item_id:
                    items[idx] = item
                    updated = True
                    break
            if not updated:
                items.append(item)
            self.save_all(collection_name, items)

    def get_by_id(self, collection_name: str, item_id: str, model_cls: Type[T], id_field: str = "id") -> Optional[T]:
        """Retrieve a single item by its ID."""
        items = self.load_all(collection_name, model_cls)
        for item in items:
            if getattr(item, id_field) == item_id:
                return item
        return None
