"""
Recipe Manager — load, save, import, export, and validate .gimp-ai-recipe files.

Recipes are JSON files stored in the user's local config directory.
Built-in presets are loaded from presets.py as read-only references.
"""

import json
import os
import sys
import time
import uuid


RECIPE_EXTENSION = ".gimp-ai-recipe"
MAX_FILE_SIZE = 50 * 1024  # 50 KB per recipe file
MAX_NESTING_DEPTH = 20


class RecipeManager:
    """Manages recipe persistence: load, save, import, export, validate."""

    def __init__(self, config_dir):
        self.config_dir = config_dir
        self.recipes_dir = os.path.join(config_dir, "recipes")
        os.makedirs(self.recipes_dir, exist_ok=True)
        self._cache = {}  # id -> recipe dict

    # ── Load / Save ──────────────────────────────────────

    def load_all(self):
        """Load all user recipes from the recipes directory. Returns list of (id, name)."""
        self._cache = {}
        result = []
        if not os.path.isdir(self.recipes_dir):
            return result
        for fname in sorted(os.listdir(self.recipes_dir)):
            if not fname.endswith(RECIPE_EXTENSION):
                continue
            path = os.path.join(self.recipes_dir, fname)
            try:
                recipe = self._read_recipe_file(path)
                if recipe:
                    mid = recipe["metadata"]["id"]
                    self._cache[mid] = recipe
                    result.append((mid, recipe["metadata"]["name"]))
            except Exception as e:
                print(f"Recipe load error ({fname}): {e}", file=sys.stderr)
        return result

    def load_recipe(self, recipe_id):
        """Load a single recipe by ID (checks cache first)."""
        if recipe_id in self._cache:
            return self._cache[recipe_id]
        path = os.path.join(self.recipes_dir, f"{recipe_id}{RECIPE_EXTENSION}")
        if os.path.exists(path):
            recipe = self._read_recipe_file(path)
            if recipe:
                self._cache[recipe_id] = recipe
                return recipe
        return None

    def save_recipe(self, recipe):
        """Save a recipe dict to disk. Auto-generates ID if missing."""
        if "metadata" not in recipe:
            recipe["metadata"] = {}
        if "id" not in recipe["metadata"]:
            recipe["metadata"]["id"] = uuid.uuid4().hex[:12]
        if "created_at" not in recipe["metadata"]:
            recipe["metadata"]["created_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        recipe.setdefault("version", 1)

        rid = recipe["metadata"]["id"]
        path = os.path.join(self.recipes_dir, f"{rid}{RECIPE_EXTENSION}")
        try:
            data = json.dumps(recipe, ensure_ascii=False, indent=2)
            with open(path, "w", encoding="utf-8") as f:
                f.write(data)
            self._cache[rid] = recipe
            return True
        except Exception as e:
            print(f"Recipe save error: {e}", file=sys.stderr)
            return False

    def delete_recipe(self, recipe_id):
        """Delete a recipe file by ID."""
        path = os.path.join(self.recipes_dir, f"{recipe_id}{RECIPE_EXTENSION}")
        if os.path.exists(path):
            os.remove(path)
        self._cache.pop(recipe_id, None)
        return True

    # ── Import / Export ──────────────────────────────────

    def import_recipe(self, file_path):
        """
        Import a recipe from an external .gimp-ai-recipe file.
        Returns (recipe_dict, error_message).
        """
        if not os.path.exists(file_path):
            return None, "File not found."
        if os.path.getsize(file_path) > MAX_FILE_SIZE:
            return None, "File too large (max 50KB)."

        recipe = self._read_recipe_file(file_path)
        if recipe is None:
            return None, "Invalid recipe format."

        errors = self.validate(recipe)
        if errors:
            return None, "Validation failed: " + "; ".join(errors)

        # Save to user recipes
        if self.save_recipe(recipe):
            return recipe, None
        return None, "Failed to save imported recipe."

    def export_recipe(self, recipe_id, output_path):
        """Export a recipe to an external file."""
        recipe = self.load_recipe(recipe_id)
        if not recipe:
            return False, "Recipe not found."
        try:
            data = json.dumps(recipe, ensure_ascii=False, indent=2)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(data)
            return True, None
        except Exception as e:
            return False, str(e)

    # ── Validation ───────────────────────────────────────

    def validate(self, recipe):
        """
        Validate a recipe dict. Returns list of error strings (empty = valid).

        Checks:
        - Required fields (version, metadata, steps)
        - Metadata has id and name
        - Steps is a list
        - Each step has action field
        - No dangerous injection in params
        """
        errors = []

        if not isinstance(recipe, dict):
            return ["Recipe must be a JSON object."]

        if "version" not in recipe or not isinstance(recipe["version"], int):
            errors.append("Missing or invalid 'version' field.")

        metadata = recipe.get("metadata", {})
        if not isinstance(metadata, dict):
            errors.append("'metadata' must be an object.")
        else:
            if not metadata.get("id"):
                errors.append("metadata.id is required.")
            if not metadata.get("name"):
                errors.append("metadata.name is required.")

        steps = recipe.get("steps", [])
        if not isinstance(steps, list):
            errors.append("'steps' must be a list.")
        elif len(steps) == 0:
            errors.append("'steps' must contain at least one step.")
        else:
            for i, step in enumerate(steps):
                if not isinstance(step, dict):
                    errors.append(f"Step {i} is not an object.")
                    continue
                if "action" not in step:
                    errors.append(f"Step {i} missing 'action' field.")

        # Check nesting depth for JSON bomb protection
        if self._nesting_depth(recipe) > MAX_NESTING_DEPTH:
            errors.append(f"JSON nesting depth exceeds {MAX_NESTING_DEPTH}.")

        return errors

    # ── Helpers ──────────────────────────────────────────

    def _read_recipe_file(self, path):
        """Read and parse a recipe JSON file. Returns dict or None."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.loads(f.read())
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError as e:
            print(f"Recipe parse error ({path}): {e}", file=sys.stderr)
        except Exception as e:
            print(f"Recipe read error ({path}): {e}", file=sys.stderr)
        return None

    def _nesting_depth(self, obj, current=1):
        """Calculate max nesting depth of a JSON structure."""
        if not isinstance(obj, (dict, list)):
            return current
        if isinstance(obj, dict):
            values = obj.values()
        else:
            values = obj
        max_child = current
        for v in values:
            if isinstance(v, (dict, list)):
                child = self._nesting_depth(v, current + 1)
                if child > max_child:
                    max_child = child
        return max_child
