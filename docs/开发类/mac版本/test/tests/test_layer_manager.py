from unittest import mock
import pytest

# 关键：在文件开头 Mock 并导入 Gimp
gi_mock = mock.Mock()
gimp_mock = mock.Mock()
gimp_mock.FillType = mock.Mock(TRANSPARENT=0)

import sys
sys.modules['gi'] = mock.Mock()
sys.modules['gi.repository'] = gi_mock
gi_mock.Gimp = gimp_mock

from gi.repository import Gimp

import mock
from core.layer_manager import (
    duplicate_layer, create_preview_layer, find_layer_by_name,
    toggle_preview_visibility, apply_preview_to_original,
    remove_preview_layer, new_layer, new_layer_group
)

def test_duplicate_layer(mock_gimp_image, mock_drawable):
    # 准备
    mock_gimp_image.get_selected_layers.return_value = [mock_drawable]
    mock_gimp_image.get_item_position.return_value = 0
    
    # 执行
    result = duplicate_layer(mock_gimp_image, "Test Copy")
    
    # 断言
    assert result == mock_drawable
    mock_drawable.copy.assert_called_once()
    mock_drawable.set_name.assert_called_with("Test Copy")
    mock_gimp_image.insert_layer.assert_called_once()

def test_find_layer_by_name(mock_gimp_image, mock_drawable):
    # 准备
    mock_gimp_image.get_layers.return_value = [mock_drawable]
    mock_drawable.get_name.return_value = "Target Layer"
    
    # 执行
    result = find_layer_by_name(mock_gimp_image, "Target Layer")
    
    # 断言
    assert result == mock_drawable
    assert find_layer_by_name(mock_gimp_image, "Non-Existent") is None

def test_toggle_preview_visibility(mock_gimp_image, mock_drawable):
    # 准备
    mock_drawable.get_visible.return_value = True
    mock_gimp_image.get_layers.return_value = [mock_drawable]
    mock_drawable.get_name.return_value = "[AI Mentor Preview]"
    
    # 执行
    result = toggle_preview_visibility(mock_gimp_image)
    
    # 断言
    assert result is True
    mock_drawable.set_visible.assert_called_with(False)

def test_new_layer(mock_gimp_image):
    # 执行
    result = new_layer(mock_gimp_image, "New Test Layer")
    
    # 断言
    assert result is not None
    mock_gimp_image.insert_layer.assert_called_once()
    result.fill.assert_called_with(Gimp.FillType.TRANSPARENT)