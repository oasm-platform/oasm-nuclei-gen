"""
Standalone scheduler for RAG data updates in the Nuclei AI Template Generator
Run this as: python scheduler.py
"""
import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config_service import ConfigService
from app.core.nuclei_service import NucleiTemplateService


# Configure logging using environment variables for basic setup
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
log_format = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
log_file_path = os.getenv("LOG_FILE_PATH", "logs/app.log")
scheduler_log_file = log_file_path.replace("app.log", "scheduler.log")

# Ensure logs directory exists
Path(scheduler_log_file).parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format=log_format,
    handlers=[
        logging.FileHandler(scheduler_log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class StandaloneRAGScheduler:
    """
    Standalone scheduler class for managing automatic RAG data updates
    """
    
    def __init__(self):
        self.settings = ConfigService.get_settings()
        self.scheduler = AsyncIOScheduler()
        self.running = False
    
    async def scheduled_rag_update(self):
        """
        Scheduled task to update RAG data automatically.
        This function runs the same logic as the update_rag_data endpoint.
        """
        try:
            logger.info("Starting scheduled RAG data update...")
            
            # Create NucleiTemplateService instance for the scheduled task
            nuclei_service = NucleiTemplateService()
            
            # Initialize RAG engine if needed
            if not nuclei_service.rag_engine.initialized:
                await nuclei_service.rag_engine.initialize()
            
            # Perform the RAG data update using templates directory from config
            templates_dir = self.settings.nuclei.templates_dir
            rag_data_path = str(Path(templates_dir).parent)
            result = await nuclei_service.rag_engine.vector_db.update_rag_data(
                rag_data_path=rag_data_path
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
        
        if not auto_update:
            logger.info("AUTO_UPDATE_TEMPLATE_NUCLEI is disabled, automatic RAG updates will not run")
            return False
        
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
            
            logger.info(f"Scheduler configured successfully - Daily RAG updates scheduled at {schedule_time}")
            return True
            
        except (ValueError, IndexError) as e:
            logger.error(f"Invalid TIME_UPDATE_TEMPLATE format '{schedule_time}'. Expected HH:MM format (e.g., '00:00', '14:30'). Error: {e}")
            logger.error("Scheduler not started due to invalid time configuration")
            return False
    
    def start(self):
        """
        Start the scheduler
        """
        if self.scheduler.running:
            logger.warning("Scheduler is already running")
            return
        
        try:
            self.scheduler.start()
            self.running = True
            logger.info("Scheduler started successfully")
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            raise
    
    def shutdown(self):
        """
        Shutdown the scheduler gracefully
        """
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            self.running = False
            logger.info("Scheduler shutdown completed")


async def main():
    """
    Main function to run the standalone scheduler
    """
    logger.info("Starting standalone RAG scheduler...")
    
    # Create scheduler instance
    scheduler = StandaloneRAGScheduler()
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        scheduler.shutdown()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Setup and start scheduler
    if scheduler.setup_scheduler():
        scheduler.start()
        
        logger.info("Scheduler is running. Press Ctrl+C to stop.")
        
        # Keep the main thread alive
        try:
            while scheduler.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down...")
        finally:
            scheduler.shutdown()
    else:
        logger.error("Failed to setup scheduler, exiting...")
        sys.exit(1)


if __name__ == "__main__":
    # Ensure logs directory exists
    Path("logs").mkdir(exist_ok=True)
    
    # Run the scheduler
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
    except Exception as e:
        logger.error(f"Scheduler failed with error: {e}")
        sys.exit(1)