#!/usr/bin/env python3
"""
Main entry point for the multilingual video dubbing system.

This system performs end-to-end video dubbing from any language to any language,
completely offline with local models.

Usage:
    python main.py <input_video> <output_video> [options]

Example:
    python main.py input.mp4 output.mp4 --target-lang es --source-lang en
"""

import argparse
import sys
from pathlib import Path

from orchestrator import DubbingOrchestrator
from configs import get_config
from utils import setup_logger


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Multilingual Video Dubbing System - Fully Local and Offline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dub video from auto-detected language to English
  python main.py input.mp4 output.mp4 --target-lang en
  
  # Dub from Spanish to French
  python main.py video.mp4 dubbed.mp4 --source-lang es --target-lang fr
  
  # Keep temporary files for debugging
  python main.py input.mp4 output.mp4 --target-lang en --keep-temp
  
  # Use custom config file
  python main.py input.mp4 output.mp4 --config my_config.yaml

Supported language codes:
  en (English), es (Spanish), fr (French), de (German), zh (Chinese),
  ja (Japanese), ko (Korean), ar (Arabic), hi (Hindi), pt (Portuguese),
  ru (Russian), it (Italian), tr (Turkish), pl (Polish), nl (Dutch),
  vi (Vietnamese), th (Thai), id (Indonesian), uk (Ukrainian), ro (Romanian)
"""
    )
    
    # Required arguments
    parser.add_argument(
        'input_video',
        type=str,
        help='Path to input video file'
    )
    
    parser.add_argument(
        'output_video',
        type=str,
        help='Path for output dubbed video'
    )
    
    # Optional arguments
    parser.add_argument(
        '--target-lang',
        type=str,
        default=None,
        help='Target language code (default: from config, usually "en")'
    )
    
    parser.add_argument(
        '--source-lang',
        type=str,
        default=None,
        help='Source language code (default: auto-detect)'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default=None,
        help='Path to custom configuration file'
    )
    
    parser.add_argument(
        '--keep-temp',
        action='store_true',
        help='Keep temporary files after processing'
    )
    
    parser.add_argument(
        '--log-level',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default=None,
        help='Logging level (default: from config)'
    )
    
    return parser.parse_args()


def validate_input(args):
    """Validate input arguments."""
    # Check input video exists
    if not Path(args.input_video).exists():
        print(f"Error: Input video not found: {args.input_video}", file=sys.stderr)
        sys.exit(1)
    
    # Check output directory exists
    output_dir = Path(args.output_video).parent
    if not output_dir.exists():
        print(f"Error: Output directory not found: {output_dir}", file=sys.stderr)
        sys.exit(1)
    
    # Check if output file already exists
    if Path(args.output_video).exists():
        response = input(f"Output file {args.output_video} already exists. Overwrite? [y/N]: ")
        if response.lower() not in ['y', 'yes']:
            print("Aborted.")
            sys.exit(0)
    
    return True


def main():
    """Main entry point."""
    # Parse arguments
    args = parse_args()
    
    # Validate input
    validate_input(args)
    
    try:
        # Load configuration
        config = get_config(args.config)
        
        # Override log level if specified
        if args.log_level:
            config.set('logging.level', args.log_level)
        
        # Set up initial logging
        setup_logger(
            name='main',
            level=config.get('logging.level', 'INFO'),
            console=True
        )
        
        # Print banner
        print("\n" + "="*80)
        print("  MULTILINGUAL VIDEO DUBBING SYSTEM")
        print("  Fully Local | Offline | End-to-End")
        print("="*80)
        print(f"\nInput:  {args.input_video}")
        print(f"Output: {args.output_video}")
        if args.source_lang:
            print(f"Source Language: {args.source_lang}")
        else:
            print("Source Language: Auto-detect")
        print(f"Target Language: {args.target_lang or config.get('languages.target', 'en')}")
        print("\n" + "="*80 + "\n")
        
        # Initialize orchestrator
        orchestrator = DubbingOrchestrator(config_path=args.config)
        
        # Process video
        results = orchestrator.process_video(
            video_path=args.input_video,
            output_path=args.output_video,
            target_language=args.target_lang,
            source_language=args.source_lang,
            keep_temp=args.keep_temp
        )
        
        # Print summary
        print("\n" + "="*80)
        print("  PROCESSING COMPLETE!")
        print("="*80)
        print(f"\n✓ Output saved to: {results['output_video']}")
        print(f"✓ Processing time: {results['processing_time_seconds']:.2f} seconds")
        print(f"✓ Detected language: {results['source_language']}")
        print(f"✓ Target language: {results['target_language']}")
        print(f"✓ Segments processed: {results['num_segments']}")
        print(f"✓ Speakers detected: {results['num_speakers']}")
        
        if args.keep_temp:
            print(f"\nTemporary files saved at: {results['temp_dir']}")
        
        print("\n" + "="*80 + "\n")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user.", file=sys.stderr)
        return 130
    
    except Exception as e:
        print(f"\n\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
