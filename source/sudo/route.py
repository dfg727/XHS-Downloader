from typing import Optional

from fastapi import APIRouter, File, Header, UploadFile
from fastapi.responses import JSONResponse

from source.module import Manager, logging

from .model import SudokuCreate, SudokuUpdate
from .module import SudokuItem

router = APIRouter(prefix="/sudo", tags=["Sudoku"])


def determine_sudoku_type(puzzle: str) -> str:
    # 移除换行、回车、制表符等格式化空白字符
    normalized = puzzle.replace("\r", "").replace("\n", "").replace("\t", "")
    # 将占位符替换为 '0' 以保证准确的长度计算
    normalized = normalized.replace(" ", "0").replace(".", "0").replace("_", "0")
    length = len(normalized)
    
    mapping = {
        9: "3*3",
        16: "4*4",
        25: "5*5",
        36: "6*6",
        49: "7*7",
        64: "8*8",
        81: "9*9",
        144: "12*12",
        256: "16*16"
    }
    
    if length in mapping:
        return mapping[length]
    
    raise ValueError(f"数独题目长度为 {length}，无法匹配标准数独类型（标准长度如 9 (3*3), 16 (4*4), 36 (6*6), 81 (9*9) 等）")


class SudokuRoute:
    def __init__(self, manager: Manager, db_obj: SudokuItem):
        self.db_obj = db_obj
        self.manager = manager

    def setup_routes(self):
        @router.get(
            "",
            summary="List Sudoku Puzzles",
            description="获取所有数独题目，可按难度和类型筛选",
            response_class=JSONResponse,
        )
        async def list_sudokus(difficulty: Optional[str] = None, type: Optional[str] = None):
            logging(self.manager.print, f"start get sudokus, difficulty: {difficulty}, type: {type}")
            return await self.db_obj.all(difficulty=difficulty, type_=type)

        @router.get(
            "/{id_}",
            summary="Get Sudoku Puzzle by ID",
            description="获取指定ID的数独题目",
            response_class=JSONResponse,
        )
        async def get_sudoku(id_: int):
            item = await self.db_obj.select(id_)
            if not item:
                return JSONResponse(status_code=404, content={"code": 404, "message": "Sudoku puzzle not found"})
            return item

        @router.post(
            "",
            summary="Save/Create Sudoku Puzzle",
            description="保存或创建数独题目",
            response_class=JSONResponse,
        )
        async def save_sudoku(sudoku: SudokuCreate):
            logging(self.manager.print, f"start creating sudoku: {sudoku.name}")
            try:
                detected_type = determine_sudoku_type(sudoku.puzzle)
            except ValueError as e:
                return JSONResponse(status_code=400, content={"code": 400, "message": f"题目格式错误: {str(e)}"})
            
            if sudoku.answer:
                try:
                    answer_type = determine_sudoku_type(sudoku.answer)
                    if answer_type != detected_type:
                        return JSONResponse(
                            status_code=400,
                            content={"code": 400, "message": f"答案类型为 {answer_type}，与题目类型 {detected_type} 不匹配"}
                        )
                except ValueError as e:
                    return JSONResponse(status_code=400, content={"code": 400, "message": f"答案格式错误: {str(e)}"})
            
            sudoku.type = detected_type
            await self.db_obj.add(**sudoku.model_dump())
            return {"code": 200, "message": "Sudoku puzzle saved successfully"}

        @router.put(
            "/{id_}",
            summary="Update Sudoku Puzzle",
            description="更新指定ID of 数独题目",
            response_class=JSONResponse,
        )
        async def update_sudoku(id_: int, sudoku: SudokuUpdate):
            logging(self.manager.print, f"start updating sudoku: {id_}")
            exist_item = await self.db_obj.select(id_)
            if not exist_item:
                return JSONResponse(status_code=404, content={"code": 404, "message": "Sudoku puzzle not found"})
            
            update_data = sudoku.model_dump(exclude_unset=True)
            
            current_puzzle = exist_item["puzzle"]
            current_answer = exist_item["answer"]
            new_puzzle = update_data.get("puzzle")
            new_answer = update_data.get("answer")
            
            puzzle_type = None
            if new_puzzle is not None:
                try:
                    puzzle_type = determine_sudoku_type(new_puzzle)
                    update_data["type"] = puzzle_type
                except ValueError as e:
                    return JSONResponse(status_code=400, content={"code": 400, "message": f"题目格式错误: {str(e)}"})
            else:
                try:
                    puzzle_type = determine_sudoku_type(current_puzzle)
                except ValueError as e:
                    return JSONResponse(status_code=400, content={"code": 400, "message": f"已有题目数据格式错误: {str(e)}"})
            
            if new_answer is not None:
                if new_answer:
                    try:
                        answer_type = determine_sudoku_type(new_answer)
                        if answer_type != puzzle_type:
                            return JSONResponse(
                                status_code=400,
                                content={"code": 400, "message": f"答案类型为 {answer_type}，与题目类型 {puzzle_type} 不匹配"}
                            )
                    except ValueError as e:
                        return JSONResponse(status_code=400, content={"code": 400, "message": f"答案格式错误: {str(e)}"})
            elif current_answer and new_puzzle is not None:
                try:
                    answer_type = determine_sudoku_type(current_answer)
                    if answer_type != puzzle_type:
                        return JSONResponse(
                            status_code=400,
                            content={"code": 400, "message": f"更新后的题目类型为 {puzzle_type}，与已有答案类型 {answer_type} 不匹配"}
                        )
                except ValueError:
                    pass
            
            await self.db_obj.update(id_, **update_data)
            return {"code": 200, "message": "Sudoku puzzle updated successfully"}

        @router.delete(
            "/{id_}",
            summary="Delete Sudoku Puzzle",
            description="删除指定ID的数独题目",
            response_class=JSONResponse,
        )
        async def delete_sudoku(id_: int):
            logging(self.manager.print, f"start deleting sudoku: {id_}")
            exist_item = await self.db_obj.select(id_)
            if not exist_item:
                return JSONResponse(status_code=404, content={"code": 404, "message": "Sudoku puzzle not found"})
            await self.db_obj.delete(id_)
            return {"code": 200, "message": "Sudoku puzzle deleted successfully"}

        @router.post(
            "/recognize",
            summary="Recognize Sudoku from Image",
            description="根据上传的图片解析数独题目 (支持 OpenAI 兼容格式接口)",
            response_class=JSONResponse,
        )
        async def recognize_sudoku(
            file: UploadFile = File(...),
            x_openai_api_key: Optional[str] = Header(None, alias="X-OpenAI-API-Key"),
            x_openai_base_url: Optional[str] = Header(None, alias="X-OpenAI-Base-URL"),
            x_openai_model: Optional[str] = Header(None, alias="X-OpenAI-Model"),
        ):
            # 1. 查找配置
            import os
            from source.module.settings import Settings

            # 加载本地配置
            config = {}
            try:
                config = Settings(self.manager.root).run()
            except Exception:
                pass

            # 确定 API Key
            api_key = x_openai_api_key
            if not api_key:
                api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                api_key = config.get("openai_api_key")

            # 确定 Base URL
            base_url = x_openai_base_url
            if not base_url:
                base_url = os.environ.get("OPENAI_BASE_URL")
            if not base_url:
                base_url = config.get("openai_base_url") or "https://api.openai.com/v1"

            # 确定 Model
            model = x_openai_model
            if not model:
                model = os.environ.get("OPENAI_MODEL")
            if not model:
                model = config.get("openai_model") or "gpt-4o-mini"

            if not api_key:
                return JSONResponse(
                    status_code=400,
                    content={
                        "code": 400,
                        "message": "未配置 OpenAI API 密钥，请在 Header 'X-OpenAI-API-Key'、环境变量 'OPENAI_API_KEY' 或设置文件 'settings.json' 中的 'openai_api_key' 配置项中提供。"
                    }
                )

            # 2. 读取文件内容并转换为 Base64
            try:
                contents = await file.read()
                import base64
                image_base64 = base64.b64encode(contents).decode("utf-8")
            except Exception as e:
                return JSONResponse(status_code=400, content={"code": 400, "message": f"文件读取失败: {str(e)}"})

            # 3. 获取 MIME 类型
            mime_type = file.content_type or "image/png"

            # 4. 调用 OpenAI Chat Completions API
            import httpx
            base_url = base_url.rstrip("/")
            url = f"{base_url}/chat/completions"

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Analyze the Sudoku grid in this image. Detect the grid size (e.g. 9x9, 6x6, 4x4) and extract the puzzle as a single flat string of digits (use '0' for empty cells). You must output your response in JSON format. The JSON must contain the keys: 'puzzle' (the flat string of digits, e.g. 81 characters for 9x9) and 'type' (the grid size format, e.g. '9x9')."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                "temperature": 0.0,
                "response_format": {"type": "json_object"}
            }

            logging(self.manager.print, f"开始请求 OpenAI 兼容接口. URL: {url}, Model: {model}")

            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(url, headers=headers, json=payload)

                logging(self.manager.print, f"收到 OpenAI 响应. HTTP 状态码: {response.status_code}")

                if response.status_code != 200:
                    logging(self.manager.print, f"请求失败, 响应内容: {response.text}")
                    return JSONResponse(
                        status_code=400,
                        content={"code": 400, "message": f"API 请求失败 ({response.status_code}): {response.text}"}
                    )

                resp_json = response.json()
                logging(self.manager.print, f"OpenAI 完整 JSON 响应: {resp_json}")
                raw_content = resp_json["choices"][0]["message"]["content"].strip()
                logging(self.manager.print, f"提取的原始文本内容: {raw_content}")
                
                # 解析 JSON 响应
                import json
                try:
                    # 过滤可能夹带的 Markdown 代码块符号
                    clean_content = raw_content
                    if clean_content.startswith("```"):
                        lines = clean_content.splitlines()
                        if len(lines) >= 2:
                            if lines[0].startswith("```json"):
                                clean_content = "\n".join(lines[1:-1])
                            elif lines[0].startswith("```"):
                                clean_content = "\n".join(lines[1:-1])
                    
                    data_dict = json.loads(clean_content)
                    text = data_dict.get("puzzle", "").strip()
                    detected_type = data_dict.get("type", "").strip()
                except Exception as json_err:
                    # 回退逻辑：如果解析 JSON 失败，尝试作为纯文本直接清洗
                    logging(self.manager.print, f"JSON 解析失败 ({str(json_err)})，尝试直接清洗原始文本")
                    text = raw_content.replace("\r", "").replace("\n", "").replace(" ", "").replace("`", "").replace("'", "").replace("\"", "")
                    detected_type = None
                
                # 过滤常见的大模型回复噪音
                text = text.replace("\r", "").replace("\n", "").replace(" ", "").replace("`", "").replace("'", "").replace("\"", "")
                logging(self.manager.print, f"净化后的数独文本: {text}")

                if not text:
                    return JSONResponse(
                        status_code=400,
                        content={"code": 400, "message": "大模型返回的数据中未提取到有效的数独题目 (puzzle) 字段。"}
                    )

                if not detected_type:
                    try:
                        detected_type = determine_sudoku_type(text)
                    except ValueError as e:
                        return JSONResponse(
                            status_code=400,
                            content={"code": 400, "message": f"大模型提取的题目格式非法，无法匹配标准数独，识别结果: {text}。错误: {str(e)}"}
                        )
                else:
                    # 校验解析出来的类型与长度推导出的类型是否匹配
                    try:
                        actual_type = determine_sudoku_type(text)
                        if detected_type != actual_type:
                            logging(self.manager.print, f"大模型返回的类型 {detected_type} 与根据长度推导的类型 {actual_type} 不一致，采用推导类型 {actual_type}")
                            detected_type = actual_type
                    except ValueError as e:
                        return JSONResponse(
                            status_code=400,
                            content={"code": 400, "message": f"大模型提取的题目格式非法，无法匹配标准数独，识别结果: {text}。错误: {str(e)}"}
                        )

                return {
                    "code": 200,
                    "data": {
                        "puzzle": text,
                        "type": detected_type
                    }
                }

            except Exception as e:
                import traceback
                traceback.print_exc()
                return JSONResponse(status_code=500, content={"code": 500, "message": f"服务器内部错误: {str(e)}"})

        return router
