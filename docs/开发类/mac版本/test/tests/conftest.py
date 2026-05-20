import sys
import os
from unittest import mock
import pytest

# ===================== 关键：先 Mock gi.repository，再导入 =====================
# 模拟 gi.repository.Gimp 和 GLib
gi_mock = mock.Mock()
gimp_mock = mock.Mock()
glib_mock = mock.Mock()

# 给 Gimp 加一些常用常量，避免测试中报错
gimp_mock.ImageBaseType = mock.Mock(RGB=0)
gimp_mock.PDBStatusType = mock.Mock(SUCCESS=0)
# 在 conftest.py 的 mock 部分加上
gimp_mock.FillType = mock.Mock()
gimp_mock.FillType.TRANSPARENT = 0  # 把常量值设为真实的 0

# 把模拟的模块加入 sys.modules
sys.modules['gi'] = mock.Mock()
sys.modules['gi.repository'] = gi_mock
gi_mock.Gimp = gimp_mock
gi_mock.GLib = glib_mock

# 现在可以安全导入了
from gi.repository import Gimp, GLib

# ===================== 你的测试 Fixture 定义 =====================
# 将项目根目录加入路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

@pytest.fixture
def mock_gimp_image():
    """模拟GIMP Image对象"""
    image = mock.Mock()
    image.get_width.return_value = 800
    image.get_height.return_value = 600
    image.get_base_type.return_value = Gimp.ImageBaseType.RGB
    image.get_selected_layers.return_value = [mock.Mock()]
    image.get_layers.return_value = []
    image.undo_group_start = mock.Mock()
    image.undo_group_end = mock.Mock()
    return image

@pytest.fixture
def mock_drawable():
    """模拟GIMP Drawable（图层）对象"""
    drawable = mock.Mock()
    drawable.get_name.return_value = "Test Layer"
    drawable.copy.return_value = drawable
    drawable.get_parent.return_value = None
    drawable.set_visible = mock.Mock()
    drawable.set_name = mock.Mock()
    return drawable

@pytest.fixture
def mock_pdb_procedure():
    """模拟GIMP PDB过程"""
    proc = mock.Mock()
    cfg = mock.Mock()
    cfg.set_property = mock.Mock()
    proc.create_config.return_value = cfg
    proc.run.return_value = [Gimp.PDBStatusType.SUCCESS]
    Gimp.get_pdb = mock.Mock(return_value=mock.Mock(lookup_procedure=mock.Mock(return_value=proc)))
    return proc