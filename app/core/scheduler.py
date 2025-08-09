"""
Automatic scheduler for RAG data updates in the Nuclei AI Agent Template Generator
"""
import logging
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.agent import NucleiAgent


logger = logging.getLogger(__name__)


class RAGScheduler:
    """
    Scheduler class for managing automatic RAG data updates
    """
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
    
    async def scheduled_rag_update(self):
        """
        Scheduled task to update RAG data automatically.
        This function runs the same logic as the update_rag_data endpoint.
        """
        try:
            logger.info("Starting scheduled RAG data update...")
            
            # Create NucleiAgent instance for the scheduled task
            nuclei_agent = NucleiAgent()
            
            # Initialize RAG engine if needed
            if not nuclei_agent.rag_engine.initialized:
                await nuclei_agent.rag_engine.initialize()
            
            # Perform the RAG data update
            result = await nuclei_agent.rag_engine.vector_db.update_rag_data(
                rag_data_path="rag_data"
            )
            
            if result["status"] == "success":
                logger.info(f"Scheduled RAG data update completed successfully: {result['templates_loaded']} templates loaded")
            elif result["status"] == "partial_failure":
                logger.warning(f"Scheduled RAG data update completed with warnings: {result['message']}")
            else:
                logger.error(f"Scheduled RAG data update failed: {result['message']}")
                
        except Exception as e:
            logger.error(f"Error in scheduled RAG data update: {e}")
    
    def setup_scheduler(self):
        """
        Setup automatic scheduling for RAG data updates based on environment variables.
        Environment variables:
        - AUTO_UPDATE_TEMPLATE_NUCLEI: Enable/disable automatic updates (true/false)
        - TIME_UPDATE_TEMPLATE: Time to run updates in HH:MM format (default: "00:00")
        """
        auto_update = os.getenv("AUTO_UPDATE_TEMPLATE_NUCLEI", "false").lower() == "true"
        
        if auto_update:
            # Parse schedule time from environment variable
            schedule_time = os.getenv("TIME_UPDATE_TEMPLATE", "00:00")
            
            try:
                # Parse HH:MM format
                time_parts = schedule_time.split(":")
                if len(time_parts) != 2:
                    raise ValueError("Invalid time format")
                
                hour = int(time_parts[0])
                minute = int(time_parts[1])
                
                # Validate time values
                if not (0 <= hour <= 23) or not (0 <= minute <= 59):
                    raise ValueError("Hour must be 0-23, minute must be 0-59")
                
                logger.info(f"AUTO_UPDATE_TEMPLATE_NUCLEI is enabled, setting up daily RAG data updates at {schedule_time}")
                
                # Schedule daily update at specified time
                self.scheduler.add_job(
                    self.scheduled_rag_update,
                    trigger=CronTrigger(hour=hour, minute=minute),
                    id="daily_rag_update",
                    name="Daily RAG Data Update",
                    replace_existing=True
                )
                
                self.scheduler.start()
                logger.info(f"Scheduler started successfully - Daily RAG updates scheduled at {schedule_time}")
                
            except (ValueError, IndexError) as e:
                logger.error(f"Invalid TIME_UPDATE_TEMPLATE format '{schedule_time}'. Expected HH:MM format (e.g., '00:00', '14:30'). Error: {e}")
                logger.error("Scheduler not started due to invalid time configuration")
                return
                
        else:
            logger.info("AUTO_UPDATE_TEMPLATE_NUCLEI is disabled, automatic RAG updates will not run")
    
    def shutdown_scheduler(self):
        """
        Shutdown the scheduler gracefully
        """
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Scheduler shutdown completed")
    
    @property
    def is_running(self):
        """
        Check if scheduler is currently running
        """
        return self.scheduler.running