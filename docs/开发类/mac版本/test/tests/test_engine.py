import mock
from core.engine import Engine, ExecutionResult

def test_engine_execute_basic(mock_gimp_image, mock_pdb_procedure):
    # 初始化引擎
    engine = Engine(mock_gimp_image)
    
    # 准备操作列表
    actions = [
        {
            "action": "brightness_contrast",
            "params": {"brightness": 50, "contrast": 20},
            "description": "Adjust brightness/contrast"
        }
    ]
    
    # 执行
    results = engine.execute(actions)
    
    # 断言
    assert len(results) == 1
    assert isinstance(results[0], ExecutionResult)
    assert results[0].success is True
    assert results[0].message == "Adjust brightness/contrast"

def test_engine_unknown_action(mock_gimp_image):
    # 初始化引擎
    engine = Engine(mock_gimp_image)
    
    # 准备未知操作
    actions = [{"action": "unknown_action", "params": {}}]
    
    # 执行
    results = engine.execute(actions)
    
    # 断言
    assert len(results) == 1
    assert results[0].success is False
    assert "Unknown action: unknown_action" in results[0].message

def test_engine_brightness_contrast_normalization(mock_gimp_image, mock_drawable, mock_pdb_procedure):
    # 初始化引擎
    engine = Engine(mock_gimp_image)
    engine._get_layer = mock.Mock(return_value=mock_drawable)
    
    # 执行高值参数（GIMP 2.x范围）
    engine._do_brightness_contrast({"brightness": 127, "contrast": -127})
    
    # 断言参数被归一化到[-1.0, 1.0]
    cfg = mock_pdb_procedure.create_config.return_value
    cfg.set_property.assert_any_call("brightness", 1.0)
    cfg.set_property.assert_any_call("contrast", -1.0)