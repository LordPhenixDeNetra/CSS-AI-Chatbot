import csv
import asyncio
import aiofiles
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
import json
import uuid
from queue import Queue
import threading
from app.utils.logging import logger

class AsyncCSVLogger:
    """Service d'enregistrement asynchrone des réponses dans des fichiers CSV"""
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        # Nouveau chemin pour les fichiers CSV d'analyse
        self.analysis_path = self.base_path / "app" / "for-analysis" / "questions-answered"
        self.csv_files = {
            "ask_question_ultra": "responses_ask_question_ultra.csv",
            "ask_question_stream_ultra": "responses_ask_question_stream_ultra.csv",
            "ask_multimodal_question": "responses_ask_multimodal_question.csv",
            "ask_multimodal_with_image": "responses_ask_multimodal_with_image.csv",
            "user_satisfaction": "user_satisfaction.csv"
        }
        
        # Queue pour les tâches d'écriture asynchrone
        self.write_queue = Queue()
        self.worker_thread = None
        self.is_running = False
        self._start_worker()
    
    def _start_worker(self):
        """Démarre le thread worker pour l'écriture asynchrone"""
        if not self.is_running:
            self.is_running = True
            self.worker_thread = threading.Thread(target=self._worker, daemon=True)
            self.worker_thread.start()
    
    def _worker(self):
        """Worker thread pour traiter la queue d'écriture"""
        while self.is_running:
            try:
                if not self.write_queue.empty():
                    task = self.write_queue.get(timeout=1)
                    if task is None:  # Signal d'arrêt
                        break
                    self._write_to_csv_sync(task)
                    self.write_queue.task_done()
                else:
                    # Petite pause si la queue est vide
                    threading.Event().wait(0.1)
            except Exception as e:
                logger.error(f"Erreur dans le worker CSV: {e}")
    
    def _write_to_csv_sync(self, task: Dict[str, Any]):
        """Écriture synchrone dans le fichier CSV"""
        try:
            endpoint_type = task["endpoint_type"]
            data = task["data"]
            
            if endpoint_type not in self.csv_files:
                logger.error(f"Type d'endpoint inconnu: {endpoint_type}")
                return
            
            # Créer le dossier d'analyse s'il n'existe pas
            self.analysis_path.mkdir(parents=True, exist_ok=True)
            
            file_path = self.analysis_path / self.csv_files[endpoint_type]
            
            # Vérifier si le fichier existe
            file_exists = file_path.exists()
            
            with open(file_path, 'a', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=data.keys())
                
                # Écrire l'en-tête si le fichier est nouveau ou vide
                if not file_exists or file_path.stat().st_size == 0:
                    writer.writeheader()
                
                writer.writerow(data)
                
        except Exception as e:
            logger.error(f"Erreur lors de l'écriture CSV: {e}")
    
    def log_ask_question_ultra(self, 
                              question: str,
                              response: str,
                              response_id: Optional[str] = None,
                              sources: Optional[list] = None,
                              confidence_score: Optional[float] = None,
                              processing_time_ms: Optional[float] = None,
                              tokens_used: Optional[int] = None,
                              model_used: Optional[str] = None,
                              cache_hit: Optional[bool] = None,
                              error_message: Optional[str] = None):
        """Enregistre une réponse de l'endpoint ask-question-ultra"""
        
        data = {
            "response_id": response_id or str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "response": response,
            "sources": json.dumps(sources) if sources else "",
            "confidence_score": confidence_score or "",
            "processing_time_ms": processing_time_ms or "",
            "tokens_used": tokens_used or "",
            "model_used": model_used or "",
            "cache_hit": cache_hit if cache_hit is not None else "",
            "error_message": error_message or ""
        }
        
        self.write_queue.put({
            "endpoint_type": "ask_question_ultra",
            "data": data
        })
    
    def log_ask_question_stream_ultra(self,
                                     question: str,
                                     response_id: Optional[str] = None,
                                     response_chunks: Optional[list] = None,
                                     final_response: Optional[str] = None,
                                     sources: Optional[list] = None,
                                     confidence_score: Optional[float] = None,
                                     processing_time_ms: Optional[float] = None,
                                     tokens_used: Optional[int] = None,
                                     model_used: Optional[str] = None,
                                     cache_hit: Optional[bool] = None,
                                     stream_duration_ms: Optional[float] = None,
                                     chunk_count: Optional[int] = None,
                                     error_message: Optional[str] = None):
        """Enregistre une réponse de l'endpoint ask-question-stream-ultra"""
        
        data = {
            "response_id": response_id or str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "response_chunks": json.dumps(response_chunks) if response_chunks else "",
            "final_response": final_response or "",
            "sources": json.dumps(sources) if sources else "",
            "confidence_score": confidence_score or "",
            "processing_time_ms": processing_time_ms or "",
            "tokens_used": tokens_used or "",
            "model_used": model_used or "",
            "cache_hit": cache_hit if cache_hit is not None else "",
            "stream_duration_ms": stream_duration_ms or "",
            "chunk_count": chunk_count or "",
            "error_message": error_message or ""
        }
        
        self.write_queue.put({
            "endpoint_type": "ask_question_stream_ultra",
            "data": data
        })
    
    def log_ask_multimodal_question(self,
                                   question: str,
                                   response_id: Optional[str] = None,
                                   images_count: Optional[int] = None,
                                   image_descriptions: Optional[list] = None,
                                   response: Optional[str] = None,
                                   sources: Optional[list] = None,
                                   confidence_score: Optional[float] = None,
                                   processing_time_ms: Optional[float] = None,
                                   tokens_used: Optional[int] = None,
                                   model_used: Optional[str] = None,
                                   cache_hit: Optional[bool] = None,
                                   multimodal_analysis: Optional[dict] = None,
                                   ocr_text: Optional[str] = None,
                                   image_similarity_scores: Optional[list] = None,
                                   error_message: Optional[str] = None):
        """Enregistre une réponse de l'endpoint ask-multimodal-question"""
        
        data = {
            "response_id": response_id or str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "images_count": images_count or "",
            "image_descriptions": json.dumps(image_descriptions) if image_descriptions else "",
            "response": response or "",
            "sources": json.dumps(sources) if sources else "",
            "confidence_score": confidence_score or "",
            "processing_time_ms": processing_time_ms or "",
            "tokens_used": tokens_used or "",
            "model_used": model_used or "",
            "cache_hit": cache_hit if cache_hit is not None else "",
            "multimodal_analysis": json.dumps(multimodal_analysis) if multimodal_analysis else "",
            "ocr_text": ocr_text or "",
            "image_similarity_scores": json.dumps(image_similarity_scores) if image_similarity_scores else "",
            "error_message": error_message or ""
        }
        
        self.write_queue.put({
            "endpoint_type": "ask_multimodal_question",
            "data": data
        })
    
    def log_ask_multimodal_with_image(self,
                                     question: str,
                                     response_id: Optional[str] = None,
                                     query_image_info: Optional[dict] = None,
                                     image_analysis: Optional[dict] = None,
                                     response: Optional[str] = None,
                                     sources: Optional[list] = None,
                                     confidence_score: Optional[float] = None,
                                     processing_time_ms: Optional[float] = None,
                                     tokens_used: Optional[int] = None,
                                     model_used: Optional[str] = None,
                                     cache_hit: Optional[bool] = None,
                                     ocr_extracted_text: Optional[str] = None,
                                     image_caption: Optional[str] = None,
                                     image_size: Optional[str] = None,
                                     image_format: Optional[str] = None,
                                     similarity_matches: Optional[list] = None,
                                     error_message: Optional[str] = None):
        """Enregistre une réponse de l'endpoint ask-multimodal-with-image"""
        
        data = {
            "response_id": response_id or str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "query_image_info": json.dumps(query_image_info) if query_image_info else "",
            "image_analysis": json.dumps(image_analysis) if image_analysis else "",
            "response": response or "",
            "sources": json.dumps(sources) if sources else "",
            "confidence_score": confidence_score or "",
            "processing_time_ms": processing_time_ms or "",
            "tokens_used": tokens_used or "",
            "model_used": model_used or "",
            "cache_hit": cache_hit if cache_hit is not None else "",
            "ocr_extracted_text": ocr_extracted_text or "",
            "image_caption": image_caption or "",
            "image_size": image_size or "",
            "image_format": image_format or "",
            "similarity_matches": json.dumps(similarity_matches) if similarity_matches else "",
            "error_message": error_message or ""
        }
        
        self.write_queue.put({
            "endpoint_type": "ask_multimodal_with_image",
            "data": data
        })
    
    def log_user_satisfaction(self,
                            satisfaction_id: str,
                            response_id: str,
                            question: str,
                            response: str,
                            is_satisfied: bool,
                            error_message: Optional[str] = None):
        """Enregistre la satisfaction utilisateur pour une réponse"""
        
        data = {
            "satisfaction_id": satisfaction_id,
            "timestamp": datetime.now().isoformat(),
            "response_id": response_id,
            "question": question,
            "response": response,
            "is_satisfied": is_satisfied,
            "error_message": error_message or ""
        }
        
        self.write_queue.put({
            "endpoint_type": "user_satisfaction",
            "data": data
        })
    
    def stop(self):
        """Arrête le service de logging"""
        self.is_running = False
        if self.worker_thread and self.worker_thread.is_alive():
            # Signal d'arrêt
            self.write_queue.put(None)
            self.worker_thread.join(timeout=5)
    
    def get_queue_size(self) -> int:
        """Retourne la taille actuelle de la queue"""
        return self.write_queue.qsize()

# Instance globale du logger CSV
csv_logger = AsyncCSVLogger()