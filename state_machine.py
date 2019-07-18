#!/usr/bin/env python3
import copy
import time
from vb_utils_ros.utils import LockedVariable
from threading import Thread


class PassingData(set):  # FIXME
    def __init__(self):
        _data = {}
        _locks = {}

    def __getattr__(self, name):
        if name[0] == "_":
            return set.__getattr__(self, name)
        else:
            return self._data[name]

    def __setattr__(self, name, value):
        if name[0] == "_":
            set.__setattr__(self, name, value)
        else:
            self._data[name] = copy.copy(value)


class AbstractState(object):
    _states = []

    def __init__(self, name, outcomes=[]):
        self.name = name
        self.outcomes = outcomes
        self._paused = LockedVariable(False)
        self._preempted = LockedVariable(False)
        self._aborted = LockedVariable(False)
        self._running = LockedVariable(False)
        self._beginning = LockedVariable(False)
        self._executing = LockedVariable(False)
        self._ending = LockedVariable(False)
        AbstractState._states.append(self)

    def _run(self, data=None):
        self.reset()
        outcome = None
        self._begin(data)
        self._executing.store(True)
        while not (self.is_preempted() or self.is_aborted() or not outcome is None):
            if self.is_paused():
                self._idle(data)
            else:
                outcome = self._execute(data)
        self._executing.store(False)
        if self.is_aborted():
            return "__aborted__"
        if self.is_preempted():
            return "__preempted__"
        self._end(data)
        return outcome

    def _begin(self, data=None):
        self._beginning.store(True)
        self.begin(data)
        self._beginning.store(False)

    def _execute(self, data=None):
        outcome = self.execute(data)
        return outcome

    def _end(self, data=None):
        self._ending.store(True)
        self.end(data)
        self._ending.store(False)

    def _pause_in(self, data=None):
        self._paused.store(True)
        self.pause_in(data)

    def _pause_out(self, data=None):
        self.pause_out(data)
        self._paused.store(False)

    def _abort(self, data=None):
        self._aborted.store(True)

    def _preempt(self, data=None):
        self._preempted.store(True)
        while self.is_beginning() or self.is_executing() or self.is_paused() or self.is_ending():
            time.sleep(0.0001)
        return True

    def _idle(self, data=None):
        self.idle(data)

    def reset(self):
        self._paused.store(False)
        self._preempted.store(False)
        self._aborted.store(False)
        self._running.store(False)
        self._beginning.store(False)
        self._ending.store(False)
        self._executing.store(False)

    def is_paused(self):
        return self._paused.retr()

    def is_preempted(self):
        return self._preempted.retr()

    def is_aborted(self):
        return self._aborted.retr()

    def is_ending(self):
        return self._ending.retr()

    def is_beginning(self):
        return self._beginning.retr()

    def is_paused(self):
        return self._paused.retr()

    def is_executing(self):
        return self._executing.retr()

    def pause(self, pause):
        if pause == False and self._paused.retr():
            self._pause_out()
        elif pause == True and not self._paused.retr():
            self._pause_in()
        return self._paused.retr()

    def begin(self, data=None):
        raise NotImplementedError

    def execute(self, data=None):
        raise NotImplementedError

    def end(self, data=None):
        raise NotImplementedError

    def pause_in(self, data=None):
        raise NotImplementedError

    def pause_out(self, data=None):
        raise NotImplementedError

    def idle(self, data=None):
        # raise NotImplementedError
        time.sleep(0.1)


class MonitoredState(AbstractState):
    _event_names = ["on_begin", "on_execute", "on_end", "on_pause_in", "on_pause_out", "on_preempt", "on_abort"]

    def __init__(self, name, event_cb, outcomes=[]):
        AbstractState.__init__(self, name, outcomes)
        self.event_cb = event_cb

    def _begin(self, data):
        Thread(target=self.event_cb, args=("on_begin",)).start()
        AbstractState._begin(self, data)

    def _execute(self, data):
        Thread(target=self.event_cb, args=("on_execute",)).start()
        return AbstractState._execute(self, data)

    def _end(self, data):
        Thread(target=self.event_cb, args=("on_end",)).start()
        AbstractState._end(self, data)

    def _pause_in(self, data=None):
        Thread(target=self.event_cb, args=("on_pause_in",)).start()
        AbstractState._pause_in(self, data)

    def _pause_out(self, data):
        Thread(target=self.event_cb, args=("on_pause_out",)).start()
        AbstractState._pause_out(self, data)

    def _preempt(self):
        Thread(target=self.event_cb, args=("on_preempt",)).start()
        AbstractState._preempt(self)

    def _abort(self, data):
        Thread(target=self.event_cb, args=("on_abort",)).start()
        AbstractState._abort(self, data)


class StateMachine(AbstractState):
    def __init__(self, name, outcomes=[], starting_data=None):
        AbstractState.__init__(self, name, outcomes)
        self.states = dict()
        self.transitions = dict()
        self.initial_state = None
        self.current_state = None

    def add_state(self, state, transitions, initial=False):
        name = state.name
        self.states[name] = state
        self.transitions[name] = transitions
        if initial:
            if self.initial_state is None:
                self.initial_state = state
                self.current_state = self.initial_state
            else:
                raise Exception("initial state already set")

    def pause_in(self, data=None):
        self.current_state._pause_in(data)

    def pause_out(self, data=None):
        self.current_state._pause_out(data)

    def begin(self, data=None):
        if self.initial_state is None:
            if len(self.states) == 0:
                raise TransitionError("State Machine %s has no states".format(self.name))
            self.initial_state = self.states.values[0]

    def execute(self, data=None):
        outcome = None
        while not (outcome in self.outcomes or self.is_aborted() or self.is_preempted()):
            outcome = self.current_state._run(data)
            if outcome is not None:
                if outcome == "__preempted__":
                    self.current_state = self.initial_state
                    outcome = None
                elif outcome == "__aborted__":
                    return outcome
                elif outcome in self.transitions[self.current_state.name]:
                    self.current_state = self.states[self.transitions[self.current_state.name][outcome]]
                elif outcome not in self.outcomes:  # outcome not in state transitions nor in Statemachine outcomes
                    raise TransitionError("outcome neither in state transitions nor in Statemachine outcomes")
        return outcome

    def end(self, data=None):
        pass

    def reset(self):
        AbstractState.reset(self)
        self.current_state = self.initial_state

    def _preempt(self):
        self._preempted.store(True)
        self.current_state._preempt()
        while self.is_beginning() or self.is_executing() or self.is_paused() or self.is_ending():
            time.sleep(0.0001)
        return True

    def preempt_restart(self, data=None):
        self._preempt()
        self.reset()
        self._run(data)
        return True


class TransitionError(Exception):
    pass
