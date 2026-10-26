import time
import json
import logging
import os
import datetime
import mimetypes
import pandas as pd
import concurrent.futures
import hashlib
import urllib.request
import threading

thread_local = threading.local()

from google import genai
from google.genai import types
from pydantic import BaseModel
from typing import Any

logger = logging.getLogger(__name__)

class CreativeAnalyzer:
    """
    A reusable processor for auditing/analyzing ad creatives using Gemini (Vertex AI).
    """

    def __init__(self,
                 client: genai.Client,
                 system_instruction: str,
                 response_schema: type[BaseModel],
                 model: str = "gemini-2.5-flash",
                 chunk_size: int = 100,
                 max_workers: int = 25,
                 context_columns: list[str] | None = None):
        """
        Initialize the CreativeAnalyzer with configuration.

        Args:
            client (genai.Client): Pre-instantiated Gemini Client.
            system_instruction (str): Custom instruction for the Gemini model.
            response_schema (type[BaseModel]): Pydantic model for structured output validation.
            model (str): Gemini model version to use. Defaults to "gemini-2.5-flash".
            chunk_size (int): Number of rows to process at a time. Defaults to 100.
            max_workers (int): Number of parallel threads for processing. Defaults to 25.
        """
        self.client = client
        self.system_instruction = system_instruction
        self.response_schema = response_schema
        self.model = model
        self.chunk_size = chunk_size
        self.max_workers = max_workers
        self.context_columns = context_columns or []
        
        self._is_vertex = getattr(client, "vertexai", False)
        try:
            self._project = client._api_client.project if self._is_vertex else None
            self._location = client._api_client.location if self._is_vertex else None
            self._api_key = client._api_client.api_key if not self._is_vertex else None
        except Exception:
            self._project = None
            self._location = None
            self._api_key = None

        if hasattr(self.response_schema, 'model_fields'):
            self.ai_fields = list(self.response_schema.model_fields.keys())
        else:
            self.ai_fields = list(self.response_schema.__fields__.keys())

        self.safety_settings = [
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
            types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
            types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
        ]

        self.generation_config = types.GenerateContentConfig(
            temperature=0.1,
            top_p=0.95,
            system_instruction=self.system_instruction,
            safety_settings=self.safety_settings,
            response_mime_type="application/json",
            response_schema=self.response_schema
        )

        mimetypes.add_type('video/webm', '.webm')

    def _get_client(self) -> genai.Client:
        if not hasattr(thread_local, "client"):
            try:
                if self._is_vertex:
                    thread_local.client = genai.Client(
                        vertexai=True, 
                        project=self._project, 
                        location=self._location
                    )
                else:
                    thread_local.client = genai.Client(api_key=self._api_key)
            except Exception as e:
                logger.warning(f"Failed to create thread-local client, falling back to original client: {e}")
                thread_local.client = self._get_client()
        return thread_local.client

    def _to_https(self, url: str) -> str:
        return "https://" + url[len("http://") :] if url.startswith("http://") else url

    def _generate_part_from_path(self, path: str) -> tuple[Any, bool]:
        """
        Prepares a part or file object for the generation request.
        Returns:
            (Part | File, is_uploaded_file): A tuple containing the part or file object, 
                                             and a boolean indicating if it was uploaded to the File API.
        """
        client = self._get_client()

        # Vertex AI mode
        if getattr(client, "vertexai", False):
            if path.startswith("gs://"):
                mime_type, _ = mimetypes.guess_type(path)
                if not mime_type:
                    mime_type = 'video/mp4' if 'video' in path or path.endswith(('.mp4', '.webm')) else 'image/jpeg'
                return types.Part.from_uri(file_uri=path, mime_type=mime_type), False
            elif path.startswith("http://") or path.startswith("https://"):
                path = self._to_https(path)
                mime_type, _ = mimetypes.guess_type(path)
                if not mime_type:
                    mime_type = 'video/mp4'
                return types.Part.from_uri(file_uri=path, mime_type=mime_type), False
            else:
                if not os.path.exists(path):
                    raise FileNotFoundError(f"Local file not found: {path}")
                mime_type, _ = mimetypes.guess_type(path)
                if not mime_type:
                    mime_type = 'video/mp4' if path.endswith(('.mp4', '.webm')) else 'image/jpeg'
                with open(path, 'rb') as f:
                    data = f.read()
                return types.Part.from_bytes(data=data, mime_type=mime_type), False

        # Google AI Studio mode (API Key)
        else:
            if path.startswith("gs://"):
                raise ValueError("gs:// URIs are only supported when using Vertex AI (GCP) mode.")
            
            if path.startswith("http://") or path.startswith("https://"):
                path = self._to_https(path)
                temp_filename = f"temp_download_{hashlib.md5(path.encode()).hexdigest()[:8]}"
                mime_type, _ = mimetypes.guess_type(path)
                ext = mimetypes.guess_extension(mime_type) if mime_type else '.mp4'
                if not ext:
                    ext = '.mp4'
                temp_path = temp_filename + ext
                
                req = urllib.request.Request(
                    path, 
                    headers={'User-Agent': 'Mozilla/5.0'}
                )
                with urllib.request.urlopen(req, timeout=30) as response, open(temp_path, 'wb') as out_file:
                    out_file.write(response.read())
                
                try:
                    uploaded_file = client.files.upload(file=temp_path)
                    uploaded_file = self._wait_for_file_active(client, uploaded_file)
                    return uploaded_file, True
                finally:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
            else:
                if not os.path.exists(path):
                    raise FileNotFoundError(f"Local file not found: {path}")
                uploaded_file = client.files.upload(file=path)
                uploaded_file = self._wait_for_file_active(client, uploaded_file)
                return uploaded_file, True

    def _wait_for_file_active(self, client: genai.Client, uploaded_file: Any) -> Any:
        while uploaded_file.state.name == "PROCESSING":
            logger.info(f"Waiting for uploaded file {uploaded_file.name} to process...")
            time.sleep(2)
            uploaded_file = client.files.get(name=uploaded_file.name)
            
        if uploaded_file.state.name == "FAILED":
            raise ValueError(f"File upload and processing failed for Gemini API: {uploaded_file.name}")
        return uploaded_file

    def _ai_analysis(self, row: dict[str, any], path_col: str) -> dict[str, any]:
        results_row = row.copy()
        results_row.update({
            "status": None,
            "error_message": None,
            "processed_at": None
        })

        for field in self.ai_fields:
            results_row[field] = None

        content = None
        is_uploaded = False
        try:
            path = row.get(path_col) if path_col else None
            if pd.isna(path):
                path = None

            prompt_parts = ["Analyze this ad creative."]
            for col in self.context_columns:
                val = row.get(col)
                if pd.notna(val) and val != "":
                    prompt_parts.append(f"{col}: {val}")
            
            prompt = "\n".join(prompt_parts)
            client = self._get_client()

            contents = []
            is_uploaded = False
            content = None
            
            if path:
                try:
                    content, is_uploaded = self._generate_part_from_path(str(path))
                    if content:
                        contents.append(content)
                except Exception as load_err:
                    logger.warning(f"Failed to load media at {path}: {load_err}. Falling back to text-only analysis.")
            
            contents.append(prompt)

            response = None
            max_empty_retries = 3
            for attempt in range(max_empty_retries + 1):
                try:
                    response = client.models.generate_content(
                        model=self.model,
                        contents=contents,
                        config=self.generation_config
                    )
                except Exception as e:
                    msg = (getattr(e, "message", str(e)) or str(e)).lower()
                    
                    if getattr(client, "vertexai", False) and path and path.startswith("http") and any(x in msg for x in ["cannot fetch content", "url_rejected", "robots.txt", "invalid argument"]):
                        logger.warning(f"Vertex AI failed to fetch {path}, falling back to inline bytes upload...")
                        try:
                            mime_type, _ = mimetypes.guess_type(path)
                            if not mime_type: mime_type = 'video/mp4' if 'video' in path or path.endswith(('.mp4', '.webm')) else 'image/jpeg'
                            
                            req = urllib.request.Request(path, headers={'User-Agent': 'Mozilla/5.0'})
                            with urllib.request.urlopen(req, timeout=30) as http_response:
                                data = http_response.read()
                                
                            fallback_part = types.Part.from_bytes(data=data, mime_type=mime_type)
                            
                            new_contents = [fallback_part if isinstance(c, types.Part) and c.file_uri else c for c in contents]
                            response = client.models.generate_content(
                                model=self.model,
                                contents=new_contents,
                                config=self.generation_config
                            )
                        except Exception as fallback_err:
                            logger.error(f"Fallback inline upload failed for {path}: {fallback_err}")
                            raise e
                    elif "temporary failure" in msg or "429" in msg or "503" in msg or "500" in msg:
                        logger.info(f"Retry attempt {attempt} for {path} due to: {msg}")
                        time.sleep(2 ** attempt)
                        continue
                    else:
                        raise e

                if response and response.text:
                    break

                if attempt < max_empty_retries:
                    logger.warning(f"Empty response for {path}. Retrying... ({attempt+1}/{max_empty_retries})")
                    time.sleep(2)

            if response:
                if not response.text:
                    raise ValueError("Empty response from Gemini")

                parsed = json.loads(response.text)
                
                results_row.update({
                    "status": "SUCCESS",
                    "error_message": None,
                    "processed_at": datetime.datetime.now().isoformat()
                })
                for field in self.ai_fields:
                    results_row[field] = parsed.get(field)

        except Exception as err:
            logger.error(f"Error processing row {row.get('id', 'unknown')}: {err}")
            results_row.update({
                "status": "FAILED",
                "error_message": str(err)[:500],
                "processed_at": datetime.datetime.now().isoformat()
            })
        finally:
            if is_uploaded and content:
                try:
                    client.files.delete(name=content.name)
                except Exception as clean_err:
                    logger.warning(f"Failed to delete uploaded file {content.name} from Gemini API: {clean_err}")

        return results_row

    def _chunkify(self, df: pd.DataFrame, chunk_size: int):
        for start in range(0, len(df), chunk_size):
            yield df[start:start + chunk_size]

    def analyze_dataframe(self, df: pd.DataFrame, path_col: str = "asset_path") -> pd.DataFrame:
        """
        Processes a DataFrame containing ad data. Deduplicates by path, runs AI analysis,
        and merges results back to the original DataFrame.
        
        Args:
            df (pd.DataFrame): Input DataFrame. Must contain an 'id' (or similar unique row identifier) and the path_col.
            path_col (str): Column name containing local file path, GCS URI, or HTTP URL.
            
        Returns:
            pd.DataFrame: The DataFrame enriched with AI analysis fields.
        """
        if path_col not in df.columns:
            raise ValueError(f"DataFrame is missing the required column: '{path_col}'")

        work_df = df.copy()
        
        dedup_keys = [path_col]
        if 'channel' in work_df.columns:
            dedup_keys.append('channel')
        if 'content_group' in work_df.columns:
            dedup_keys.append('content_group')
            
        unique_df = work_df.drop_duplicates(subset=dedup_keys)
        logger.info(f"Deduplication: Reduced {len(work_df)} source rows to {len(unique_df)} unique assets.")

        all_results = []
        chunks = self._chunkify(unique_df, self.chunk_size)

        for idx, chunk_df in enumerate(chunks):
            if chunk_df.empty:
                continue
            logger.info(f"Processing chunk {idx + 1} with {len(chunk_df)} rows...")
            records = chunk_df.to_dict('records')
            
            chunk_results = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {executor.submit(self._ai_analysis, row, path_col): row for row in records}
                for i, future in enumerate(concurrent.futures.as_completed(futures)):
                    try:
                        res = future.result()
                        chunk_results.append(res)
                    except Exception as exc:
                        failed_row = futures[future]
                        logger.error(f"Row {failed_row.get('id')} generated exception: {exc}")
            
            all_results.extend(chunk_results)

        if all_results:
            results_df = pd.DataFrame(all_results)
            cols_to_merge = dedup_keys + self.ai_fields + ['status', 'error_message', 'processed_at']
            cols_to_merge = [c for c in cols_to_merge if c in results_df.columns]
            
            cols_to_overwrite = [c for c in (self.ai_fields + ['status', 'error_message', 'processed_at']) if c in work_df.columns]
            if cols_to_overwrite:
                work_df = work_df.drop(columns=cols_to_overwrite)

            merged_df = pd.merge(work_df, results_df[cols_to_merge], how='left', on=dedup_keys)
            return merged_df

        return work_df
