#!/usr/bin/env python3
# validation_verification_script.py
"""
Verification script to ensure NO validations were removed or changed.
Compares backup (original) executor files with refactored executor files.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Set

# Approach directories
APPROACHES = [
    'CONSISTENT_MOMENTUM',
    'CONSISTENT_VOLUME_ANCHOR', 
    'VOLUME_SPIKE_CONFIRMATION',
    'VRA'
]

BASE_PATH = Path('/Users/tech/dev/development/trending_and_summary/src/stockreports/alert/approach')

def extract_validation_calls(code: str) -> Set[str]:
    """Extract all validation-related calls from executor code."""
    
    validations = set()
    
    # Find all validator.validate_* calls
    validator_calls = re.findall(r'self\.validator\.validate_\w+\(', code)
    validations.update(validator_calls)
    
    # Find all analyzer.* calls
    analyzer_calls = re.findall(r'self\.analyzer\.\w+\(', code)
    validations.update(analyzer_calls)
    
    # Find all validation checks (if not checks)
    validation_checks = re.findall(r'if (?:not )?.*(?:_validate|is_valid)', code)
    validations.update([str(check) for check in validation_checks[:20]])  # Limit to 20
    
    # Find self.validations.append calls
    validation_appends = re.findall(r'self\.validations\.append\([^)]*\)', code)
    validations.update(validation_appends)
    
    # Find self.next_validation calls
    next_val_calls = re.findall(r'self\.next_validation\(\)', code)
    validations.update([f'self.next_validation() - count: {len(next_val_calls)}'])
    
    return validations

def extract_log_calls(code: str) -> List[str]:
    """Extract all log calls (important for validation tracking)."""
    
    logs = re.findall(r'log\([^)]*message="[^"]*"', code, re.DOTALL)
    return logs[:50]  # Return first 50 to avoid clutter

def count_validation_steps(code: str) -> int:
    """Count number of validation steps (self.next_step() calls)."""
    return len(re.findall(r'self\.next_step\(\)', code))

def analyze_approach(approach_name: str) -> Dict:
    """Analyze an approach for validation changes."""
    
    backup_file = BASE_PATH / approach_name / '.backup' / 'executor.py.bak'
    refactored_file = BASE_PATH / approach_name / 'executor.py'
    
    if not backup_file.exists():
        return {'status': 'BACKUP_NOT_FOUND', 'path': str(backup_file)}
    
    if not refactored_file.exists():
        return {'status': 'REFACTORED_NOT_FOUND', 'path': str(refactored_file)}
    
    # Read files
    with open(backup_file, 'r') as f:
        backup_code = f.read()
    
    with open(refactored_file, 'r') as f:
        refactored_code = f.read()
    
    # Extract validations
    backup_validations = extract_validation_calls(backup_code)
    refactored_validations = extract_validation_calls(refactored_code)
    
    # Count steps
    backup_steps = count_validation_steps(backup_code)
    refactored_steps = count_validation_steps(refactored_code)
    
    # Extract logs to understand validation flow
    backup_logs = extract_log_calls(backup_code)
    refactored_logs = extract_log_calls(refactored_code)
    
    # Find differences
    removed = backup_validations - refactored_validations
    added = refactored_validations - backup_validations
    preserved = backup_validations & refactored_validations
    
    return {
        'status': 'ANALYZED',
        'approach': approach_name,
        'backup_validation_count': len(backup_validations),
        'refactored_validation_count': len(refactored_validations),
        'backup_steps': backup_steps,
        'refactored_steps': refactored_steps,
        'preserved_validations': len(preserved),
        'removed_validations': list(removed)[:10],  # Show first 10
        'added_validations': list(added)[:10],      # Show first 10
        'backup_logs_count': len(backup_logs),
        'refactored_logs_count': len(refactored_logs),
        'backup_file_size': backup_file.stat().st_size,
        'refactored_file_size': refactored_file.stat().st_size,
    }

def main():
    """Run validation verification for all approaches."""
    
    print("=" * 80)
    print("VALIDATION VERIFICATION REPORT")
    print("=" * 80)
    print()
    
    results = {}
    for approach in APPROACHES:
        print(f"Analyzing {approach}...")
        result = analyze_approach(approach)
        results[approach] = result
        print(f"  Status: {result['status']}")
        
        if result['status'] == 'ANALYZED':
            print(f"  Backup Validation Calls: {result['backup_validation_count']}")
            print(f"  Refactored Validation Calls: {result['refactored_validation_count']}")
            print(f"  Preserved: {result['preserved_validations']}")
            print(f"  Backup Steps: {result['backup_steps']}")
            print(f"  Refactored Steps: {result['refactored_steps']}")
            
            if result['removed_validations']:
                print(f"  ⚠️ REMOVED (first 10): {result['removed_validations']}")
            if result['added_validations']:
                print(f"  ✅ ADDED (first 10): {result['added_validations']}")
        print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    for approach, result in results.items():
        if result['status'] == 'ANALYZED':
            removed = result['removed_validations']
            step_match = result['backup_steps'] == result['refactored_steps']
            
            status = "✅" if not removed and step_match else "⚠️"
            print(f"{status} {approach}: {result['preserved_validations']} preserved, " +
                  f"{len(removed)} removed, step_count_match: {step_match}")

if __name__ == '__main__':
    main()
