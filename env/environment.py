from env.models import SQLObservation
from env.grader import grade_query
from tasks.easy_task import TASK as EASY
from tasks.medium_task import TASK as MEDIUM
from tasks.hard_task import TASK as HARD

class SQLEnv:

    def __init__(self):
        self.tasks = [EASY, MEDIUM, HARD]
        self.current_task = None
        self.step_count = 0

    async def reset(self):
        self.current_task = self.tasks[0]
        self.step_count = 0

        obs = SQLObservation(
            schema=self.current_task["schema"],
            broken_query=self.current_task["broken_query"],
            last_result=None
        )

        return {
            "observation": obs,
            "reward": 0,
            "done": False,
            "info": {}
        }

    async def step(self, action):
        self.step_count += 1

        reward = grade_query(
            action.query,
            self.current_task["expected_query"]
        )

        done = reward == 1.0 or self.step_count > 5

        obs = SQLObservation(
            schema=self.current_task["schema"],
            broken_query=self.current_task["broken_query"],
            last_result=action.query
        )

        return {
            "observation": obs,
            "reward": reward,
            "done": done,
            "info": {}
        }

    def state(self):
        return {
            "step_count": self.step_count
        }