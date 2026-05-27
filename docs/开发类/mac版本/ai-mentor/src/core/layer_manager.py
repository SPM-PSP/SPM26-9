"""
Layer manager module.

Handles non-destructive editing: layer duplication, adjustment layers,
layer groups, masks, undo grouping, and preview layer management.
"""

import gi
gi.require_version('Gimp', '3.0')
from gi.repository import Gimp
from gi.repository import GLib

import sys

PREVIEW_LAYER_NAME = "[AI Mentor Preview]"


def duplicate_layer(image, name="AI Copy"):
    """
    Duplicate the active layer for non-destructive editing.
    Returns the new layer, or None on failure.
    """
    try:
        layers = image.get_selected_layers()
        if not layers:
            return None
        original = layers[0]
        new_layer = original.copy()
        if not new_layer:
            return None
        new_layer.set_name(name)
        image.insert_layer(new_layer, original.get_parent(),
                           image.get_item_position(original) + 1)
        return new_layer
    except Exception as e:
        print(f"Layer duplicate error: {e}", file=sys.stderr)
        return None


def create_preview_layer(image):
    """
    Create or reuse a preview layer for non-destructive editing.
    If a layer named [AI Mentor Preview] already exists, select and return it.
    Otherwise duplicate the active layer with the preview name.
    """
    try:
        existing = find_layer_by_name(image, PREVIEW_LAYER_NAME)
        if existing:
            image.set_selected_layers([existing])
            return existing
        return duplicate_layer(image, PREVIEW_LAYER_NAME)
    except Exception as e:
        print(f"Preview layer error: {e}", file=sys.stderr)
        return duplicate_layer(image, PREVIEW_LAYER_NAME)


def find_layer_by_name(image, name):
    """Search all layers for one with the given name. Returns layer or None."""
    layers = image.get_layers()
    if not layers:
        return None
    for layer in layers:
        if layer.get_name() == name:
            return layer
    return None


def toggle_preview_visibility(image):
    """
    Toggle the visibility of the [AI Mentor Preview] layer.
    Returns True if the layer was found and toggled.
    """
    layer = find_layer_by_name(image, PREVIEW_LAYER_NAME)
    if layer:
        layer.set_visible(not layer.get_visible())
        return True
    return False


def is_preview_visible(image):
    """Check if the preview layer is visible."""
    layer = find_layer_by_name(image, PREVIEW_LAYER_NAME)
    if layer:
        return layer.get_visible()
    return False


def apply_preview_to_original(image):
    """
    Merge the preview layer down onto the original.
    Returns True on success.
    """
    layer = find_layer_by_name(image, PREVIEW_LAYER_NAME)
    if not layer:
        return False
    try:
        # Select the preview layer
        image.set_selected_layers([layer])
        # Merge down
        result = image.merge_down(layer, Gimp.MergeType.CLIP_TO_IMAGE)
        return result is not None
    except Exception as e:
        print(f"Apply preview error: {e}", file=sys.stderr)
        return False


def remove_preview_layer(image):
    """Remove the preview layer, discarding changes."""
    layer = find_layer_by_name(image, PREVIEW_LAYER_NAME)
    if layer:
        try:
            image.remove_layer(layer)
            return True
        except Exception as e:
            print(f"Remove preview error: {e}", file=sys.stderr)
    return False


def new_layer(image, name="New Layer", width=None, height=None,
              layer_type=None, opacity=100, mode=Gimp.LayerMode.NORMAL):
    """Create a new transparent layer."""
    try:
        if width is None:
            width = image.get_width()
        if height is None:
            height = image.get_height()
        if layer_type is None:
            if image.get_base_type() == Gimp.ImageBaseType.RGB:
                layer_type = Gimp.ImageType.RGBA_IMAGE
            else:
                layer_type = Gimp.ImageType.GRAYA_IMAGE

        layer = Gimp.Layer.new(image, name, width, height, layer_type,
                               opacity, mode)
        layer.fill(Gimp.FillType.TRANSPARENT)
        image.insert_layer(layer, None, 0)
        return layer
    except Exception as e:
        print(f"New layer error: {e}", file=sys.stderr)
        return None


def new_layer_group(image, name="Group"):
    """Create a new layer group."""
    try:
        group = Gimp.GroupLayer.new(image)
        group.set_name(name)
        image.insert_layer(group, None, 0)
        return group
    except Exception as e:
        print(f"Layer group error: {e}", file=sys.stderr)
        return None


def add_white_mask(layer):
    """Add a white (fully opaque) layer mask."""
    try:
        mask = layer.create_mask(Gimp.AddMaskType.WHITE)
        layer.add_mask(mask)
        return mask
    except Exception as e:
        print(f"Mask error: {e}", file=sys.stderr)
        return None


def add_black_mask(layer):
    """Add a black (fully transparent) layer mask."""
    try:
        mask = layer.create_mask(Gimp.AddMaskType.BLACK)
        layer.add_mask(mask)
        return mask
    except Exception as e:
        print(f"Mask error: {e}", file=sys.stderr)
        return None


def merge_visible(image):
    """Merge all visible layers into one."""
    try:
        result = image.merge_visible_layers(Gimp.MergeType.CLIP_TO_IMAGE)
        return result
    except Exception as e:
        print(f"Merge error: {e}", file=sys.stderr)
        return None


def flatten_image(image):
    """Flatten image (merge all layers)."""
    try:
        image.flatten()
    except Exception as e:
        print(f"Flatten error: {e}", file=sys.stderr)


def get_active_drawable(image):
    """Get the currently active paintable drawable."""
    layers = image.get_selected_layers()
    if layers:
        return layers[0]
    return image.get_active_drawable()


def get_selection_bounds(image):
    """Return (x1, y1, x2, y2) if a selection exists, else None."""
    try:
        # In GIMP 3.0, try get_selection_bounds on the image
        bounds = image.get_selection_bounds()
        if bounds:
            # Returns (non_empty, x1, y1, x2, y2)
            if bounds[0]:
                return (bounds[1], bounds[2], bounds[3], bounds[4])
        return None
    except Exception:
        try:
            mask = image.get_selection()
            if mask:
                non_empty, x1, y1, x2, y2 = mask.get_bounds()
                if non_empty:
                    return (x1, y1, x2, y2)
        except Exception:
            pass
    return None
