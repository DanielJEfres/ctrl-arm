import yaml
import os
from typing import Dict, Optional, Any


class GestureKeyMapper:
    def __init__(self, config_path: str | None = None):
        env_path = os.getenv("CTRLARM_CONFIG")
        if config_path is None:
            if env_path and os.path.exists(env_path):  
                config_path = env_path
            elif env_path:
                pass
            
            if not env_path or not os.path.exists(env_path):
                base_dir = os.path.dirname(__file__)
                project_root = os.path.abspath(os.path.join(base_dir, "..", ".."))
                config_path = os.path.join(project_root, "hardware", "config.yaml")
                
        self.config_path = os.path.abspath(config_path)
        self.config = self._load_config()
        self.current_mode = self.config.get("active_profile", "default_mode")

    def save_config(self) -> bool:
        import tempfile, shutil
        try:
            tmp = tempfile.NamedTemporaryFile(delete=False, dir=os.path.dirname(self.config_path))
            with open(tmp.name, "w") as f:
                yaml.safe_dump(self.config, f, default_flow_style=False, sort_keys=False)
            shutil.move(tmp.name, self.config_path)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False


    def _load_config(self) -> Dict[str, Any]:
        try:
            with open(self.config_path, "r") as f:
                config = yaml.safe_load(f)
                return config or {}
        except Exception as e:
            print(f"Error loading gesture config from {self.config_path}: {e}")
            return {}

    def set_mode(self, mode: str) -> bool:
        if mode in self.config.get("modes", {}):
            self.current_mode = mode
            return True
        return False

    def get_current_mode(self) -> str:
        return self.current_mode

    def get_available_modes(self) -> list:
        return list(self.config.get("modes", {}).keys())

    def get_key_for_gesture(self, gesture: str, mode: str | None = None) -> Optional[str]:
        if mode is None:
            mode = self.current_mode
        if gesture not in self.config.get("gesture_labels", []):
            return None
        current_keys = self.config.get("current_keys", {})
        if gesture in current_keys and current_keys[gesture] is not None:
            return current_keys[gesture]
        mode_overrides = self.config.get("mode_key_overrides", {}).get(mode, {})
        if gesture in mode_overrides:
            return mode_overrides[gesture]
        default_keys = self.config.get("default_gesture_keys", {})
        return default_keys.get(gesture)

    def get_all_keys_for_mode(self, mode: str | None = None) -> Dict[str, Optional[str]]:
        if mode is None:
            mode = self.current_mode
        result: Dict[str, Optional[str]] = {}
        for gesture in self.config.get("gesture_labels", []):
            result[gesture] = self.get_key_for_gesture(gesture, mode)
        return result

    def update_gesture_key(self, gesture: str, key: str, mode: str | None = None) -> bool:
        if gesture not in self.config.get("gesture_labels", []):
            return False
        if "current_keys" not in self.config:
            self.config["current_keys"] = {}
        self.config["current_keys"][gesture] = key
        return True

    def set_current_keys_from_mode(self, mode: str) -> bool:
        if mode not in self.config.get("modes", {}):
            return False
        self.current_mode = mode
        self.config["active_profile"] = mode
        self.config["current_keys"] = self.get_all_keys_for_mode(mode)
        return True


    def select_mode_for_app(self, app_name: str) -> str:
        mapping = self.config.get("app_mode_mapping", {})
        for app, mode in mapping.items():
            if app.lower() in app_name.lower():
                return mode
        return "default_mode"

    def reset_mode_to_defaults(self, mode: str) -> bool:
        if mode in self.config.get("mode_key_overrides", {}):
            del self.config["mode_key_overrides"][mode]
            return True
        return False

    def get_mode_info(self, mode: str | None = None) -> Dict[str, Any]:
        if mode is None:
            mode = self.current_mode
        return {
            "mode": mode,
            "mode_id": self.config.get("modes", {}).get(mode, -1),
            "gesture_keys": self.get_all_keys_for_mode(mode),
            "has_overrides": mode in self.config.get("mode_key_overrides", {}),
        }
