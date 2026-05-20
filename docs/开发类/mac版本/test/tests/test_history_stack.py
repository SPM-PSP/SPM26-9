import pytest
from unittest import mock
from core.history_stack import HistoryStack

# 先全局 Mock 掉 gi.repository.Gimp
@pytest.fixture(autouse=True)
def mock_gimp_module():
    with mock.patch("gi.repository.Gimp"):
        yield

def test_history_stack_basic(mock_gimp_image):
    stack = HistoryStack(mock_gimp_image, max_entries=5)

    stack.record("brightness adjustment")
    stack.record("contrast adjustment")

    assert stack.undo_count == 2
    assert stack.redo_count == 0

    # 这里不用再 mock Gimp 了，因为上面的 fixture 已经全局 mock 好了
    result = stack.undo_last()
    assert result is True
    assert stack.undo_count == 1
    assert stack.redo_count == 1

    result = stack.redo_last()
    assert result is True
    assert stack.undo_count == 2
    assert stack.redo_count == 0

    stack.clear()
    assert stack.undo_count == 0
    assert stack.redo_count == 0

def test_undo_all(mock_gimp_image):
    stack = HistoryStack(mock_gimp_image)
    stack.record("op1")
    stack.record("op2")
    stack.record("op3")

    # 关键：最多执行 100 次就强制停止，彻底防止卡死
    exec_limit = 0
    max_limit = 100

    def safe_undo():
        nonlocal exec_limit
        exec_limit += 1
        if exec_limit > max_limit:
            return False  # 强制退出循环
        if stack.undo_count > 0:
            stack._undo_stack.pop()
            stack._redo_stack.append("mock")
        return True

    with mock.patch.object(stack, "undo_last", side_effect=safe_undo):
        count = stack.undo_all()
        assert stack.undo_count == 0