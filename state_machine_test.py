#!/usr/bin/env python3
from state_machine import MonitoredState, PassingData, StateMachine, AbstractState, TransitionError
import unittest
import time
import asyncio
from threading import Thread, Timer
from multiprocessing import Process
from unittest.mock import Mock


class TestState(AbstractState):
    def __init__(self, name, outcomes=[], execute_iterations=3):
        AbstractState.__init__(self, name, outcomes)
        self.test_begin = 0
        self.test_execute = 0
        self.test_end = 0
        self.test_pause_in = 0
        self.test_pause_out = 0
        self.test_idle = 0
        self.mock = Mock()
        self.execute_iterations = execute_iterations

    def begin(self, data=None):
        self.mock.begin()
        self.test_begin += 1
        time.sleep(0.01)

    def execute(self, data=None):
        self.mock.execute()
        self.test_execute += 1
        time.sleep(0.01)
        return self.outcomes[0] if self.test_execute >= self.execute_iterations else None

    def end(self, data=None):
        self.mock.end()
        self.test_end += 1
        time.sleep(0.01)

    def pause_in(self, data=None):
        self.mock.pause_in()
        print("+++++++++++++++++++++++")
        self.test_pause_in += 1
        time.sleep(0.01)

    def pause_out(self, data=None):
        self.mock.pause_out()
        print("-----------------------")
        self.test_pause_out += 1
        time.sleep(0.01)

    def idle(self, data=None):
        self.mock.idle()
        print("ooooooooooooooooooooooo")
        self.test_idle += 1
        time.sleep(0.01)

    def __str__(self):
        s = (
            "Test State : "
            + str(self.name)
            + "\n outcomes : "
            + str(self.outcomes)
            + "\n test_begin :"
            + str(self.test_begin)
            + "\n test_execute :"
            + str(self.test_execute)
            + "\n test_end :"
            + str(self.test_end)
            + "\n test_pause_in :"
            + str(self.test_pause_in)
            + "\n test_pause_out :"
            + str(self.test_pause_out)
            + "\n test_idle :"
            + str(self.test_idle)
        )
        return s


class PreemptThread(Thread):
    def __init__(self, state_preempted):
        Thread.__init__(self)
        self.state_preempted = state_preempted

    def run(self):
        print("preempted ", self.state_preempted.name)
        self.state_preempted._preempt()


class PauseThread(Thread):
    def __init__(self, state_paused, pause_time=0.03):
        Thread.__init__(self)
        self.state_paused = state_paused
        self.pause_time = pause_time

    def run(self):
        print("paused ", self.state_paused.name)
        self.state_paused._pause_in()
        time.sleep(self.pause_time)
        self.state_paused._pause_out()


class TestBasicStateMachine(unittest.TestCase):
    def setUp(self):
        self.iterations_num = 3
        self.sm = StateMachine("test_state_machine", ["exit", "__preempted__"])
        self.state1 = TestState("test1", ["s2", "s3"], execute_iterations=self.iterations_num)
        self.state2 = TestState("test2", ["s3", "s1"], execute_iterations=self.iterations_num)
        self.state3 = TestState("test3", ["exit", "s1"], execute_iterations=self.iterations_num)
        self.sm.add_state(self.state1, {"s2": "test2", "s3": "test3"}, initial=True)
        self.sm.add_state(self.state2, {"s1": "test1", "s3": "test3"})
        self.sm.add_state(self.state3, {"s2": "test2", "s1": "test1"})

    def test_basic(self):
        start_time = time.time()
        self.sm._run()
        execution_time = time.time() - start_time
        print("execution_time ", execution_time)
        self.state1.mock.begin.assert_called()
        assert self.state1.mock.begin.call_count == 1
        self.state1.mock.execute.assert_called()
        assert self.state1.mock.execute.call_count == self.iterations_num
        self.state1.mock.end.assert_called()
        assert self.state1.mock.end.call_count == 1
        self.state2.mock.begin.assert_called()
        assert self.state2.mock.begin.call_count == 1
        self.state2.mock.execute.assert_called()
        assert self.state2.mock.execute.call_count == self.iterations_num
        self.state2.mock.end.assert_called()
        assert self.state2.mock.end.call_count == 1
        self.state3.mock.begin.assert_called()
        assert self.state3.mock.begin.call_count == 1
        self.state3.mock.execute.assert_called()
        assert self.state3.mock.execute.call_count == self.iterations_num
        self.state3.mock.end.assert_called()
        assert self.state3.mock.end.call_count == 1

    def test_pause(self):
        execution = Thread(target=self.sm._run)
        execution.start()
        time.sleep(0.02)
        PauseThread(self.sm, 0.03).start()
        execution.join()
        self.state1.mock.begin.assert_called()
        assert self.state1.mock.begin.call_count == 1
        self.state1.mock.pause_in.assert_called()
        assert self.state1.mock.pause_in.call_count == 1
        self.state1.mock.pause_out.assert_called()
        assert self.state1.mock.pause_out.call_count == 1
        self.state1.mock.execute.assert_called()
        assert self.state1.mock.execute.call_count == self.iterations_num
        self.state1.mock.end.assert_called()
        assert self.state1.mock.end.call_count == 1
        self.state2.mock.begin.assert_called()
        assert self.state2.mock.begin.call_count == 1
        self.state2.mock.execute.assert_called()
        assert self.state2.mock.execute.call_count == self.iterations_num
        self.state2.mock.end.assert_called()
        assert self.state2.mock.end.call_count == 1
        self.state3.mock.begin.assert_called()
        assert self.state3.mock.begin.call_count == 1
        self.state3.mock.execute.assert_called()
        assert self.state3.mock.execute.call_count == self.iterations_num
        self.state3.mock.end.assert_called()
        assert self.state3.mock.end.call_count == 1

    def test_pause_twice(self):
        execution = Thread(target=self.sm._run)
        execution.start()
        time.sleep(0.03)
        PauseThread(self.sm, 0.03).start()
        time.sleep(0.03)
        PauseThread(self.sm, 0.03).start()
        execution.join()
        self.state1.mock.begin.assert_called()
        assert self.state1.mock.begin.call_count == 1
        self.state1.mock.pause_in.assert_called()
        assert self.state1.mock.pause_in.call_count == 2
        self.state1.mock.pause_out.assert_called()
        assert self.state1.mock.pause_out.call_count == 2
        self.state1.mock.execute.assert_called()
        assert self.state1.mock.execute.call_count == self.iterations_num
        self.state1.mock.end.assert_called()
        assert self.state1.mock.end.call_count == 1
        self.state2.mock.begin.assert_called()
        assert self.state2.mock.begin.call_count == 1
        self.state2.mock.execute.assert_called()
        assert self.state2.mock.execute.call_count == self.iterations_num
        self.state2.mock.end.assert_called()
        assert self.state2.mock.end.call_count == 1
        self.state3.mock.begin.assert_called()
        assert self.state3.mock.begin.call_count == 1
        self.state3.mock.execute.assert_called()
        assert self.state3.mock.execute.call_count == self.iterations_num
        self.state3.mock.end.assert_called()
        assert self.state3.mock.end.call_count == 1

    def test_preempt(self):
        execution = Thread(target=self.sm._run, args=())
        execution.start()
        time.sleep(0.03)
        PreemptThread(self.sm).start()
        execution.join()
        self.state1.mock.begin.assert_called()
        assert self.state1.mock.begin.call_count == 1
        self.state1.mock.execute.assert_called()
        assert self.state1.mock.execute.call_count <= self.iterations_num
        self.state1.mock.end.assert_not_called()
        self.state2.mock.begin.assert_not_called()
        self.state2.mock.execute.assert_not_called()
        self.state2.mock.end.assert_not_called()
        self.state3.mock.begin.assert_not_called()
        self.state3.mock.execute.assert_not_called()
        self.state3.mock.end.assert_not_called()

    def test_restart_after_preempt(self):
        execution = Thread(target=self.sm._run, args=())
        execution.start()
        time.sleep(0.04)
        PreemptThread(self.sm).start()
        execution.join()
        time.sleep(0.01)
        execution2 = Thread(target=self.sm._run, args=())
        execution2.start()
        execution2.join()
        self.state1.mock.begin.assert_called()
        assert self.state1.mock.begin.call_count == 2
        self.state1.mock.execute.assert_called()
        assert self.state1.mock.execute.call_count >= self.iterations_num
        self.state1.mock.end.assert_called()
        assert self.state1.mock.end.call_count == 1
        self.state2.mock.begin.assert_called()
        assert self.state2.mock.begin.call_count == 1
        self.state2.mock.execute.assert_called()
        assert self.state2.mock.execute.call_count == self.iterations_num
        self.state2.mock.end.assert_called()
        assert self.state2.mock.end.call_count == 1
        self.state3.mock.begin.assert_called()
        assert self.state3.mock.begin.call_count == 1
        self.state3.mock.execute.assert_called()
        assert self.state3.mock.execute.call_count == self.iterations_num
        self.state3.mock.end.assert_called()
        assert self.state3.mock.end.call_count == 1

    def test_preempt_while_paused(self):
        print("test_preempt_while_paused")
        execution = Thread(target=self.sm._run)
        execution.start()
        time.sleep(0.02)
        PauseThread(self.sm, 0.03).start()
        PreemptThread(self.sm).start()
        time.sleep(0.03)
        Thread(target=self.sm._pause_out, args=()).start()
        execution.join()
        assert self.state1.mock.pause_in.call_count == 1
        self.state1.mock.end.assert_not_called()
        self.state2.mock.begin.assert_not_called()
        self.state2.mock.execute.assert_not_called()
        self.state2.mock.end.assert_not_called()
        self.state3.mock.begin.assert_not_called()
        self.state3.mock.execute.assert_not_called()
        self.state3.mock.end.assert_not_called()


class TestVerticalStackStateMachines(unittest.TestCase):  # TODO : add asserts
    def setUp(self):
        self.base_sm = StateMachine("test_state_machine", ["exit", "__preempted__"])
        self.state1 = TestState("test1", ["s2"])
        self.state2 = TestState("test2", ["s3"])
        self.state3 = TestState("test3", ["exit"])
        self.base_sm.add_state(self.state1, {"s2": "test2"}, initial=True)
        self.base_sm.add_state(self.state2, {"s3": "test3"})
        self.base_sm.add_state(self.state3, {})
        self.sms = []
        self.sms.append(self.base_sm)
        for i in range(100):
            sm = StateMachine("test_state_machine" + str(i), ["exit"])
            sm.add_state(self.sms[i], {}, initial=True)
            self.sms.append(sm)
        self.top_sm = self.sms[-1]

    def test_basic(self):
        start_time = time.time()
        print(self.top_sm._run())
        execution_time = time.time() - start_time
        print("execution_time ", execution_time)
        print(self.state1, "\n")
        print(self.state2, "\n")
        print(self.state3, "\n")

    def test_pause(self):
        execution = Thread(target=self.top_sm._run)
        execution.start()
        time.sleep(0.02)
        PauseThread(self.top_sm, 0.03).start()
        execution.join()
        print(self.state1, "\n")
        print(self.state2, "\n")
        print(self.state3, "\n")

    def test_preempt(self):
        execution = Thread(target=self.top_sm._run, args=())
        execution.start()
        time.sleep(0.03)
        start_preempt_time = time.time()
        PreemptThread(self.top_sm).start()
        execution.join()
        preempt_time = time.time() - start_preempt_time
        print("preempt_time ", preempt_time)
        print(self.state1, "\n")
        print(self.state2, "\n")
        print(self.state3, "\n")

    def test_restart_after_preempt(self):
        execution = Thread(target=self.top_sm._run, args=())
        execution.start()
        time.sleep(0.1)
        PreemptThread(self.top_sm).start()
        execution.join()
        time.sleep(0.1)
        execution2 = Thread(target=self.top_sm._run, args=())
        execution2.start()
        execution2.join()
        print(self.state1, "\n")
        print(self.state2, "\n")
        print(self.state3, "\n")


class TestStateLoop(TestState):
    def __init__(self, name, outcomes=[], execute_iterations=3):
        TestState.__init__(self, name, outcomes, execute_iterations)

    def execute(self, data=None):
        self.test_execute += 1
        time.sleep(0.01)
        if self.test_execute >= self.execute_iterations:
            return self.outcomes[1]
        return self.outcomes[0]


class TestLoopStateMachine(unittest.TestCase):
    def setUp(self):
        self.sm = StateMachine("test_state_machine", ["exit", "__preempted__"])
        self.state1 = TestStateLoop("test1", ["s2", "s3"])
        self.state2 = TestStateLoop("test2", ["s1", "s1"])
        self.state3 = TestStateLoop("test3", ["s1", "exit"])
        self.sm.add_state(self.state1, {"s2": "test2", "s3": "test3"}, initial=True)
        self.sm.add_state(self.state2, {"s1": "test1"})
        self.sm.add_state(self.state3, {"s1": "test1"})

    def test_basic(self):
        start_time = time.time()
        self.sm._run()
        execution_time = time.time() - start_time
        print("execution_time ", execution_time)
        print(self.state1, "\n")
        print(self.state2, "\n")
        print(self.state3, "\n")


class TestTransitionErrorStateMachine(unittest.TestCase):
    def setUp(self):
        self.sm = StateMachine("test_state_machine", ["exit", "__preempted__"])
        self.state1 = TestStateLoop("test1", ["s2", "s3"])
        self.state2 = TestStateLoop("test2", ["s1", "s1"])
        self.state3 = TestStateLoop("test3", ["s1", "exit"])
        self.sm.add_state(self.state1, {"s2": "test2", "s3": "test3"}, initial=True)
        self.sm.add_state(self.state2, {"s1": "test1"})
        self.sm.add_state(self.state3, {"s1": "test1"})

    def test_no_states(self):
        error = None
        try:
            StateMachine("test_state_machine", [])._run()
        except TransitionError as e:
            error = e
        assert error is not None

    def test_transition_doesnt_exist(self):
        error = None
        sm = StateMachine("test_state_machine", ["exit", "__preempted__"])
        state1 = TestState("test1", ["s2"])
        sm.add_state(self.state1, {}, initial=True)
        try:
            sm._run()
        except TransitionError as e:
            error = e
            print(error)
        assert error is not None


class TestMonitoredState(MonitoredState):
    def __init__(self, name, event_cb, outcomes=[], execute_iterations=3):
        MonitoredState.__init__(self, name, event_cb, outcomes)
        self.test_begin = 0
        self.test_execute = 0
        self.test_end = 0
        self.test_pause_in = 0
        self.test_pause_out = 0
        self.test_idle = 0
        self.execute_iterations = execute_iterations

    def begin(self, data=None):
        self.test_begin += 1
        time.sleep(0.01)

    def execute(self, data=None):
        print("State : ", self.name)
        self.test_execute += 1
        time.sleep(0.01)

        return self.outcomes[0] if self.test_execute >= self.execute_iterations else None

    def end(self, data=None):
        self.test_end += 1
        time.sleep(0.01)

    def pause_in(self, data=None):
        print("+++++++++++++++++++++++")
        self.test_pause_in += 1
        time.sleep(0.01)

    def pause_out(self, data=None):
        print("-----------------------")
        self.test_pause_out += 1
        time.sleep(0.01)

    def idle(self, data=None):
        print("ooooooooooooooooooooooo")
        self.test_idle += 1
        time.sleep(0.01)

    def __str__(self):
        s = (
            "Test State : "
            + str(self.name)
            + "\n outcomes : "
            + str(self.outcomes)
            + "\n test_begin :"
            + str(self.test_begin)
            + "\n test_execute :"
            + str(self.test_execute)
            + "\n test_end :"
            + str(self.test_end)
            + "\n test_pause_in :"
            + str(self.test_pause_in)
            + "\n test_pause_out :"
            + str(self.test_pause_out)
            + "\n test_idle :"
            + str(self.test_idle)
        )
        return s


class AbortingState(MonitoredState):
    def begin(self, data=None):
        pass

    def execute(self, data=None):
        self._abort(data)
        return None


class TestMonitoredStateMachine(unittest.TestCase):
    def setUp(self):
        self.mock = Mock()

        self.iterations_num = 3
        self.sm = StateMachine("test_state_machine", ["exit"])
        self.state1 = TestMonitoredState(
            "test1", outcomes=["s2"], event_cb=self.mock, execute_iterations=self.iterations_num
        )
        self.state2 = TestMonitoredState(
            "test2", outcomes=["s3"], event_cb=self.mock, execute_iterations=self.iterations_num
        )
        self.state3 = TestMonitoredState(
            "test3", outcomes=["exit"], event_cb=self.mock, execute_iterations=self.iterations_num
        )
        self.sm.add_state(self.state1, {"s2": "test2"}, initial=True)
        self.sm.add_state(self.state2, {"s3": "test3"})
        self.sm.add_state(self.state3, {})
        self.mock.reset_mock()

    def test_basic(self):
        print("_____run______")
        self.sm._run()
        time.sleep(0.04)
        assert self.mock.call_count == (self.iterations_num + 2) * 3
        self.mock.assert_any_call("on_begin")
        self.mock.assert_any_call("on_execute")
        self.mock.assert_any_call("on_end")

    def test_pause(self):
        print("_____pause______")
        execution = Thread(target=self.sm._run)
        execution.start()
        time.sleep(0.02)
        PauseThread(self.sm, 0.03).start()
        execution.join()
        time.sleep(0.02)
        assert self.mock.call_count == (self.iterations_num + 2) * 3 + 2

        # check cb called with pause_in and pause_out once and only once
        self.mock.assert_any_call("on_pause_in")
        self.mock.assert_any_call("on_pause_out")
        self.mock.assert_any_call("on_begin")
        self.mock.assert_any_call("on_execute")
        self.mock.assert_any_call("on_end")

    def test_preempt(self):
        print("_____preempt______")
        execution = Thread(target=self.sm._run)
        execution.start()
        PreemptThread(self.sm).start()
        execution.join()
        time.sleep(0.04)
        self.mock.assert_any_call("on_begin")
        self.mock.assert_called_with("on_preempt")

    def test_abort(self):
        print("_____abort______")
        sm = StateMachine("test_state_machine", ["exit", "__preempted__"])
        state = AbortingState("test1", self.mock, ["exit"])
        sm.add_state(state, {}, initial=True)
        execution = Thread(target=sm._run)
        execution.start()
        execution.join()
        self.mock.assert_any_call("on_begin")
        self.mock.assert_any_call("on_execute")
        self.mock.assert_called_with("on_abort")
        assert self.mock.call_count == 3


if __name__ == "__main__":
    unittest.main()
