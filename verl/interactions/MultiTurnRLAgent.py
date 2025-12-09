# my_project/interactions/external_api.py
import os
import asyncio
import random
from typing import Any, Optional
from uuid import uuid4

from openai import AsyncOpenAI

from .base import BaseInteraction
import sys
from pathlib import Path
# 手动指定 Benchmark 包所在的目录
BENCHMARK_PATH = "/algorithm_nas/algorithm_nas/naifan/multi_turn_rl/env/sandbox"

benchmark_dir = Path(BENCHMARK_PATH).resolve()
if str(benchmark_dir) not in sys.path:
    sys.path.insert(0, str(benchmark_dir))

from Benchmark.orchestrator.chat_loop_epj import (
    init_external_epj_session,
    process_external_test_model_reply,
)
import logging
logger = logging.getLogger(__file__)
logger.setLevel(os.getenv("VERL_LOGGING_LEVEL", "WARN"))

def get_context_reward(result: dict):
    '''
    提取所有对话和对应的Reward
    '''
    history = result['history']
    
    rewards = []
    for r in result['epj']['trajectory']:
        # 暂且将distance作为Reward
        rewards.append(r['distance'])
    return history, rewards

class MultiTurnRLAgent(BaseInteraction):
    """
    - 从 messages 中取最近一条 assistant 文本
    - 作为 user 输入请求外部 Chat Completions
    - 返回外部回复作为环境响应；仅用 max_rounds 控制终止
    - 本实现不计算回合奖励（恒 0.0）
    """

    def __init__(self, config: dict):
        super().__init__(config)
        print(f"config: {config}")
        self._instance_dict: dict[str, dict[str, Any]] = {}

    async def start_interaction(self, instance_id: Optional[str] = None, **kwargs) -> str:
        #print(f"start_interaction: {instance_id} ")
        if instance_id is None:
            instance_id = str(uuid4())
        # 目标是重新得到scipt id，然后初始化session
        # 替换data数据中初始化的actor回复

        logger.warning(f"kwargs: {kwargs}")    
        session = None
        self._instance_dict[instance_id] = {
            "session": session,
            "turn": 0,
        }
        return instance_id

    async def generate_response(
        self, instance_id: str, messages: list[dict[str, Any]], **kwargs
    ) -> tuple[bool, str, float, dict]:

        # 调用完整的多轮对话
        """

        流程：
        1. 获取当前session状态，session统一在self._instance_dict里维护
        2. 外部获得模型回复后，调用 process_external_test_model_reply(session, reply)
        3. 每轮拿到新的 Actor 回复，再发给被测模型；若返回 should_continue=False 则对话结束
        """

        session = self._instance_dict[instance_id]["session"]
        turn = self._instance_dict[instance_id]["turn"]
        model_reply = messages[-1]['content']
        logger.warning(f"[TestModel 第{turn}轮] {model_reply}")

        # 将模型回复送入 EPJ，获取下一句 Actor + 评估信息
        result = process_external_test_model_reply(session, model_reply)

        # 更新session
        self._instance_dict[instance_id]["session"] = result['session']

        # 若终止，输出原因并结束
        if not result.get("should_continue", True):
            logger.warning(f"[对话结束] 原因: {result.get('termination_reason')}, 类型: {result.get('termination_type')}")

        # 正常继续，取出下一句 Actor 回复
        actor_msg = result["actor_reply"]
        print(f"[Actor 回复] {actor_msg}")

        # 如当前轮触发评估，可查看 state_packet
        if result.get("state_packet"):
            sp = result["state_packet"]
            print(f"[评分] 距离: {sp.get('distance_to_goal')}, 在区间: {sp.get('is_in_zone')}")


        self._instance_dict[instance_id]["turn"] += 1
        if self._instance_dict[instance_id]["turn"] >= self._instance_dict[instance_id]["max_turns"]:
            return True, actor_msg, 100
        else:
            return False, actor_msg, -100

    async def calculate_score(self, instance_id: str, **kwargs) -> float:
        '''
        好像没什么用
        '''
        return 100

    async def finalize_interaction(self, instance_id: str, **kwargs) -> None:
        if instance_id in self._instance_dict:
            del self._instance_dict[instance_id]