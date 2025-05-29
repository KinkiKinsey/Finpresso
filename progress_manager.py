#!/usr/bin/env python3
# progress_manager.py - Enhanced progress tracking system
import threading
import time
from typing import Dict, Optional
from job_registry import jobs

class ProgressManager:
    """
    Enhanced progress manager with smooth animations and accurate tracking
    """
    def __init__(self):
        self.progress_threads: Dict[str, threading.Thread] = {}
        self.target_progress: Dict[str, Dict[str, float]] = {}
        self.current_progress: Dict[str, Dict[str, float]] = {}
        self.progress_locks: Dict[str, threading.Lock] = {}
        self.active = True
        
        # Define progress milestones for each panel
        self.milestones = {
            "macro": {
                "init": 5,
                "data_loading": 15,
                "analysis_start": 25,
                "processing": 50,
                "inference": 70,
                "finalization": 85,
                "save_complete": 95,
                "done": 100
            },
            "micro": {
                "init": 5,
                "news_fetch": 15,
                "news_analysis": 30,
                "fundamental_start": 40,
                "financial_analysis": 55,
                "competitive_analysis": 70,
                "synthesis": 85,
                "save_complete": 95,
                "done": 100
            },
            "price": {
                "init": 5,
                "data_fetch": 15,
                "technical_analysis": 30,
                "pattern_recognition": 45,
                "graph_generation": 60,
                "graph_saving": 75,
                "strategy_formulation": 85,
                "verification": 95,
                "done": 100
            },
            "strategy": {
                "init": 10,
                "data_integration": 30,
                "mindmap_generation": 60,
                "final_synthesis": 85,
                "save_complete": 95,
                "done": 100
            }
        }
        
    def start_job(self, job_id: str):
        """Initialize progress tracking for a new job"""
        self.target_progress[job_id] = {
            "macro": 0,
            "micro": 0,
            "price": 0,
            "strategy": 0
        }
        self.current_progress[job_id] = {
            "macro": 0,
            "micro": 0,
            "price": 0,
            "strategy": 0
        }
        self.progress_locks[job_id] = threading.Lock()
        
        # Start the smooth progress update thread
        thread = threading.Thread(target=self._smooth_progress_updater, args=(job_id,))
        thread.daemon = True
        thread.start()
        self.progress_threads[job_id] = thread
        
    def update_progress(self, job_id: str, panel: str, milestone: str):
        """Update progress to a specific milestone"""
        if job_id not in self.target_progress:
            return
            
        if panel in self.milestones and milestone in self.milestones[panel]:
            with self.progress_locks[job_id]:
                self.target_progress[job_id][panel] = self.milestones[panel][milestone]
                
    def set_panel_complete(self, job_id: str, panel: str):
        """Mark a panel as 100% complete"""
        if job_id not in self.target_progress:
            return
            
        with self.progress_locks[job_id]:
            self.target_progress[job_id][panel] = 100
            self.current_progress[job_id][panel] = 100
            
        # Update job registry immediately
        if job_id in jobs:
            jobs[job_id].panel_progress[panel] = 100
            
    def _smooth_progress_updater(self, job_id: str):
        """Background thread to smoothly update progress"""
        while self.active and job_id in self.target_progress:
            try:
                with self.progress_locks[job_id]:
                    # Smoothly increment progress towards target
                    for panel in ["macro", "micro", "price", "strategy"]:
                        current = self.current_progress[job_id][panel]
                        target = self.target_progress[job_id][panel]
                        
                        if current < target:
                            # Calculate smooth increment (faster when far, slower when close)
                            diff = target - current
                            increment = max(0.5, diff * 0.15)  # 15% of remaining distance
                            new_progress = min(target, current + increment)
                            
                            self.current_progress[job_id][panel] = new_progress
                            
                            # Update job registry
                            if job_id in jobs:
                                jobs[job_id].panel_progress[panel] = int(new_progress)
                
                # Check if job is complete
                if all(self.current_progress[job_id][p] >= 100 for p in ["macro", "micro", "price", "strategy"]):
                    break
                    
            except Exception as e:
                print(f"Error in progress updater: {e}")
                
            time.sleep(0.1)  # Update 10 times per second for smooth animation
            
    def cleanup_job(self, job_id: str):
        """Clean up resources for a completed job"""
        if job_id in self.target_progress:
            del self.target_progress[job_id]
        if job_id in self.current_progress:
            del self.current_progress[job_id]
        if job_id in self.progress_locks:
            del self.progress_locks[job_id]
        if job_id in self.progress_threads:
            del self.progress_threads[job_id]
            
    def shutdown(self):
        """Shutdown the progress manager"""
        self.active = False

# Global progress manager instance
progress_manager = ProgressManager()

# Enhanced progress tracking functions to replace the old ones
def init_progress(job_id: str):
    """Initialize progress tracking for a job"""
    progress_manager.start_job(job_id)
    
def update_progress(job_id: str, panel: str, milestone: str):
    """Update progress to a specific milestone"""
    progress_manager.update_progress(job_id, panel, milestone)
    
def complete_panel(job_id: str, panel: str):
    """Mark a panel as complete"""
    progress_manager.set_panel_complete(job_id, panel)
    
def cleanup_progress(job_id: str):
    """Clean up progress tracking for a completed job"""
    progress_manager.cleanup_job(job_id)