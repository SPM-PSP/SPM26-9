from core.state_machine import GuideStateMachine, State

def test_state_machine_initial_state():
    # 初始化
    sm = GuideStateMachine()
    
    # 断言初始状态
    assert sm.state == State.IDLE
    assert sm.context == {}

def test_state_transitions_valid():
    # 初始化
    sm = GuideStateMachine()
    
    # 有效转换：IDLE → ANALYZING
    assert sm.can_transition(State.ANALYZING)
    assert sm.transition(State.ANALYZING, reason="start analysis") is True
    assert sm.state == State.ANALYZING
    assert sm.context == {"reason": "start analysis"}
    
    # 有效转换：ANALYZING → GUIDING
    assert sm.can_transition(State.GUIDING)
    assert sm.transition(State.GUIDING) is True
    assert sm.state == State.GUIDING

def test_state_transitions_invalid():
    # 初始化
    sm = GuideStateMachine()
    sm.transition(State.ANALYZING)
    
    # 无效转换：ANALYZING → EXECUTING（不在允许列表）
    assert not sm.can_transition(State.EXECUTING)
    assert sm.transition(State.EXECUTING) is False
    assert sm.state == State.ANALYZING

def test_state_machine_listener():
    # 初始化
    sm = GuideStateMachine()
    callback_calls = []
    
    # 注册回调
    def callback(old, new, ctx):
        callback_calls.append((old, new, ctx))
    
    sm.subscribe(callback)
    
    # 触发转换
    sm.transition(State.ANALYZING, test="123")
    
    # 断言回调
    assert len(callback_calls) == 1
    assert callback_calls[0] == (State.IDLE, State.ANALYZING, {"test": "123"})
    
    # 重置状态
    sm.reset()
    assert sm.state == State.IDLE
    assert len(callback_calls) == 2