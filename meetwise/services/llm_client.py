# -*- coding: utf-8 -*-
"""
大语言模型调用模块
封装智谱 GLM-4.5-Air API，提供摘要生成和对话功能
智谱 API 兼容 OpenAI 接口格式
"""

import logging
from openai import OpenAI

logger = logging.getLogger(__name__)


class LLMClient:
    """智谱 GLM API 客户端"""

    def __init__(self, api_key, base_url="https://open.bigmodel.cn/api/paas/v4/", model="glm-4.5-air"):
        """
        初始化 LLM 客户端
        :param api_key: 智谱 API Key
        :param base_url: API 接口地址
        :param model: 模型名称
        """
        logger.info(f"[LLMClient] 初始化客户端 - base_url: {base_url}, model: {model}")
        logger.info(f"[LLMClient] API Key: {api_key[:10]}...{api_key[-4:] if api_key else 'None'}")
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    def generate_summary(self, transcript):
        """
        生成会议摘要
        :param transcript: 完整转写文本（格式："发言人1：内容\n发言人2：内容"）
        :return: 结构化摘要文本（Markdown 格式）
        """
        logger.info(f"[LLMClient] 开始生成摘要，转写文本长度: {len(transcript)} 字符")

        if not transcript or not transcript.strip():
            logger.warning("[LLMClient] 转写文本为空，无法生成摘要")
            return "暂无会议内容，无法生成摘要。"

        prompt = f"""你是一位专业的会议纪要助手。请根据以下会议转写内容，生成结构化摘要。

要求：
1. 直接输出结构化内容，不要在开头添加"会议纪要"之类的标题
2. **关键点**：列出 3-5 个核心讨论要点，每个要点用一句话概括
3. **待办事项**：列出需要后续跟进的任务，标注负责人（如果能从对话中识别出来的话）
4. **结论**：总结会议达成的共识和决定

请使用 Markdown 格式输出，结构清晰，语言简洁。

会议内容：
{transcript}"""

        try:
            logger.info(f"[LLMClient] 调用 API 生成摘要，模型: {self._model}")
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": "你是一位专业的会议纪要助手，擅长从对话中提取关键信息并生成结构化摘要。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            result = response.choices[0].message.content
            logger.info(f"[LLMClient] 摘要生成成功，结果长度: {len(result)} 字符")
            return result
        except Exception as e:
            logger.error(f"[LLMClient] 摘要生成失败: {type(e).__name__}: {str(e)}", exc_info=True)
            return f"摘要生成失败: {str(e)}"

    def chat(self, transcript, question, history=None):
        """
        基于会议内容的 AI 对话
        :param transcript: 完整转写文本
        :param question: 用户问题
        :param history: 历史对话记录 [{"question": str, "answer": str}, ...]
        :return: AI 回答文本
        """
        logger.info(f"[LLMClient] 开始 AI 对话，问题: {question[:50]}...")

        if not question or not question.strip():
            logger.warning("[LLMClient] 问题为空")
            return "请输入您的问题。"

        # 构造上下文
        context = f"以下是会议的完整转写内容：\n\n{transcript}" if transcript else "暂无会议内容。"
        logger.info(f"[LLMClient] 转写文本长度: {len(transcript)} 字符")

        # 构造消息列表
        messages = [
            {"role": "system", "content": "你是一位会议纪要助手，请基于会议内容准确回答用户的问题。如果问题与会议内容无关，请礼貌地提醒用户。回答要简洁、准确、有条理。"}
        ]

        # 添加会议内容
        messages.append({"role": "system", "content": context})

        # 添加历史对话（最近 5 轮）
        if history:
            logger.info(f"[LLMClient] 加载历史对话: {len(history)} 轮")
            for h in history[-5:]:
                messages.append({"role": "user", "content": h["question"]})
                messages.append({"role": "assistant", "content": h["answer"]})

        # 添加当前问题
        messages.append({"role": "user", "content": question})

        try:
            logger.info(f"[LLMClient] 调用 API 进行对话，模型: {self._model}")
            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=0.5,
                max_tokens=1500
            )
            result = response.choices[0].message.content
            logger.info(f"[LLMClient] 对话成功，回答长度: {len(result)} 字符")
            return result
        except Exception as e:
            logger.error(f"[LLMClient] 对话失败: {type(e).__name__}: {str(e)}", exc_info=True)
            return f"对话请求失败: {str(e)}"

    def test_connection(self):
        """测试 API 连接是否正常"""
        logger.info("[LLMClient] 开始测试 API 连接...")
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": "你好"}],
                max_tokens=10
            )
            logger.info("[LLMClient] API 连接测试成功")
            return True, "API 连接正常"
        except Exception as e:
            logger.error(f"[LLMClient] API 连接测试失败: {type(e).__name__}: {str(e)}", exc_info=True)
            return False, f"API 连接失败: {str(e)}"
