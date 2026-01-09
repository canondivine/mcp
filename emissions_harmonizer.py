#!/usr/bin/env python3
"""
ECU Emissions System Harmonizer
Identifies and reports on emissions control logic that needs harmonization
when physical components (DPF, EGR, Throttle Valve) have been removed
"""

import struct
import sys
import os
from typing import Dict, List, Tuple, Optional
import json
from datetime import datetime

class EmissionsHarmonizer:
    """
    Harmonizer for ECU calibrations with physically removed emissions components
    Identifies retained logic for DPF, EGR, and throttle valve systems
    """
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.data = bytearray()
        self.filesize = 0
        self.issues = []
        self.recommendations = []
        
    def load_file(self) -> bool:
        """Load ECU binary file"""
        try:
            with open(self.filepath, 'rb') as f:
                self.data = bytearray(f.read())
            self.filesize = len(self.data)
            print(f"[+] Loaded: {self.filepath} ({self.filesize} bytes)")
            return True
        except Exception as e:
            print(f"[-] Error: {e}")
            return False
    
    def check_dpf_regeneration_logic(self) -> Dict:
        """
        Check for active DPF regeneration logic
        DPF regeneration should be completely disabled if DPF is removed
        """
        print("\n[*] Checking DPF regeneration logic...")
        
        findings = {
            'status': 'CHECKING',
            'issues_found': [],
            'active_patterns': [],
            'disabled_patterns': []
        }
        
        # Pattern 1: Look for non-zero DPF regeneration temperature thresholds
        # Typical values: 550-650°C (stored as 5500-6500 in 0.1°C units)
        dpf_temp_threshold_count = 0
        for i in range(0, len(self.data) - 2, 2):
            val = struct.unpack('>H', self.data[i:i+2])[0]
            if 5000 <= val <= 7000:  # Potential DPF regen temp
                dpf_temp_threshold_count += 1
                findings['active_patterns'].append({
                    'offset': hex(i),
                    'value': val,
                    'celsius': val / 10,
                    'type': 'DPF_REGEN_TEMP_THRESHOLD'
                })
        
        # Pattern 2: Look for DPF pressure differential thresholds
        # Typical values: 50-300 mbar
        dpf_pressure_count = 0
        for i in range(0, len(self.data) - 2, 2):
            val = struct.unpack('>H', self.data[i:i+2])[0]
            if 50 <= val <= 300:
                dpf_pressure_count += 1
        
        # Pattern 3: Check for zero-filled regions (properly disabled)
        zero_regions = self._find_zero_regions(min_length=16)
        findings['disabled_patterns'] = [{
            'offset': hex(region[0]),
            'length': region[1],
            'type': 'ZERO_FILLED_REGION'
        } for region in zero_regions[:20]]
        
        if dpf_temp_threshold_count > 100:
            findings['issues_found'].append({
                'severity': 'HIGH',
                'component': 'DPF',
                'issue': 'Active regeneration temperature thresholds detected',
                'count': dpf_temp_threshold_count,
                'impact': 'ECU may attempt DPF regeneration causing rich fuel mixture and performance issues',
                'recommendation': 'Set all DPF regeneration temperature thresholds to 0 or maximum value to prevent activation'
            })
        
        findings['status'] = 'CRITICAL' if findings['issues_found'] else 'OK'
        print(f"[{'!' if findings['issues_found'] else '+'}] DPF Status: {findings['status']}")
        
        return findings
    
    def check_egr_control_logic(self) -> Dict:
        """
        Check for active EGR control logic
        EGR valve control should be disabled if EGR is removed
        """
        print("\n[*] Checking EGR control logic...")
        
        findings = {
            'status': 'CHECKING',
            'issues_found': [],
            'active_egr_maps': [],
            'egr_position_commands': []
        }
        
        # Pattern 1: Look for EGR position command values (0-100%)
        # Should all be 0% if EGR is removed
        egr_position_count = 0
        non_zero_egr_positions = []
        
        for i in range(0, len(self.data) - 1):
            val = self.data[i]
            # Check for percentage values in typical EGR range
            if 1 <= val <= 100:
                # Check surrounding context to confirm it's likely EGR related
                if i > 10 and i < len(self.data) - 10:
                    context = self.data[i-10:i+10]
                    # If surrounded by similar percentage values, likely an EGR map
                    similar_values = sum(1 for b in context if 0 <= b <= 100)
                    if similar_values > 15:
                        egr_position_count += 1
                        non_zero_egr_positions.append({
                            'offset': hex(i),
                            'value': val,
                            'percentage': val
                        })
        
        # Pattern 2: Look for EGR torque compensation tables
        # These should be zeroed if EGR is removed
        torque_compensation_patterns = self._find_sequential_patterns(
            min_val=10, max_val=200, min_length=8
        )
        
        if egr_position_count > 50:
            findings['issues_found'].append({
                'severity': 'HIGH',
                'component': 'EGR',
                'issue': 'Active EGR position command values detected',
                'count': egr_position_count,
                'impact': 'ECU attempting to control non-existent EGR valve, causing torque compensation errors',
                'recommendation': 'Set all EGR position maps to 0% to prevent valve control attempts'
            })
        
        if len(torque_compensation_patterns) > 10:
            findings['issues_found'].append({
                'severity': 'MEDIUM',
                'component': 'EGR',
                'issue': 'EGR torque compensation tables appear active',
                'count': len(torque_compensation_patterns),
                'impact': 'Incorrect torque calculations due to compensation for non-existent EGR flow',
                'recommendation': 'Zero out all EGR torque compensation tables'
            })
        
        findings['active_egr_maps'] = non_zero_egr_positions[:50]
        findings['status'] = 'CRITICAL' if findings['issues_found'] else 'OK'
        print(f"[{'!' if findings['issues_found'] else '+'}] EGR Status: {findings['status']}")
        
        return findings
    
    def check_throttle_valve_logic(self) -> Dict:
        """
        Check for active throttle valve control logic
        Throttle valve should remain fully open if removed
        """
        print("\n[*] Checking throttle valve control logic...")
        
        findings = {
            'status': 'CHECKING',
            'issues_found': [],
            'throttle_position_maps': [],
            'modulation_patterns': []
        }
        
        # Pattern 1: Look for throttle position values that aren't 100% (fully open)
        # Throttle should be locked at 100% if valve is removed
        throttle_modulation_count = 0
        
        for i in range(0, len(self.data) - 1):
            val = self.data[i]
            # Look for throttle values less than 100% (indicating modulation)
            if 10 <= val <= 95:  # Not fully open
                # Check context
                if i > 5 and i < len(self.data) - 5:
                    context = self.data[i-5:i+5]
                    # If surrounded by similar values, likely a throttle map
                    similar = sum(1 for b in context if 10 <= b <= 100)
                    if similar > 7:
                        throttle_modulation_count += 1
                        findings['throttle_position_maps'].append({
                            'offset': hex(i),
                            'value': val,
                            'percentage': val
                        })
        
        # Pattern 2: Check for throttle valve modulation during DPF regen
        # This should be disabled
        modulation_sequences = self._find_sequential_patterns(
            min_val=20, max_val=80, min_length=6
        )
        
        if throttle_modulation_count > 100:
            findings['issues_found'].append({
                'severity': 'HIGH',
                'component': 'THROTTLE_VALVE',
                'issue': 'Active throttle valve modulation detected',
                'count': throttle_modulation_count,
                'impact': 'ECU attempting to modulate non-existent throttle valve, causing airflow calculation errors',
                'recommendation': 'Set all throttle position maps to 100% (fully open) or disable throttle control'
            })
        
        if len(modulation_sequences) > 20:
            findings['issues_found'].append({
                'severity': 'MEDIUM',
                'component': 'THROTTLE_VALVE',
                'issue': 'Throttle modulation sequences detected',
                'count': len(modulation_sequences),
                'impact': 'Throttle valve modulation during regeneration attempts',
                'recommendation': 'Disable all throttle modulation logic'
            })
        
        findings['status'] = 'CRITICAL' if findings['issues_found'] else 'OK'
        print(f"[{'!' if findings['issues_found'] else '+'}] Throttle Status: {findings['status']}")
        
        return findings
    
    def check_lambda_sensor_logic(self) -> Dict:
        """
        Check lambda sensor control logic
        May need adjustment if emissions equipment removed
        """
        print("\n[*] Checking lambda sensor control logic...")
        
        findings = {
            'status': 'CHECKING',
            'issues_found': [],
            'lambda_targets': []
        }
        
        # Look for lambda target values (typically 0.8-1.2, stored as 800-1200)
        lambda_count = 0
        for i in range(0, len(self.data) - 2, 2):
            val = struct.unpack('>H', self.data[i:i+2])[0]
            if 700 <= val <= 1300:
                lambda_count += 1
                findings['lambda_targets'].append({
                    'offset': hex(i),
                    'value': val,
                    'lambda': val / 1000
                })
        
        # Rich lambda targets (< 1.0) may indicate DPF regen logic
        rich_targets = [t for t in findings['lambda_targets'] if t['lambda'] < 0.95]
        
        if len(rich_targets) > 50:
            findings['issues_found'].append({
                'severity': 'MEDIUM',
                'component': 'LAMBDA',
                'issue': 'Rich lambda targets detected (likely for DPF regeneration)',
                'count': len(rich_targets),
                'impact': 'Rich fuel mixture for non-existent DPF regeneration',
                'recommendation': 'Review and adjust lambda targets to stoichiometric or lean values'
            })
        
        findings['status'] = 'WARNING' if findings['issues_found'] else 'OK'
        print(f"[{'!' if findings['issues_found'] else '+'}] Lambda Status: {findings['status']}")
        
        return findings
    
    def check_nox_sensor_logic(self) -> Dict:
        """
        Check NOx sensor and SCR control logic
        Should be disabled if emissions equipment removed
        """
        print("\n[*] Checking NOx sensor and SCR logic...")
        
        findings = {
            'status': 'CHECKING',
            'issues_found': [],
            'nox_thresholds': []
        }
        
        # Look for NOx threshold values (typically 50-500 ppm)
        nox_count = 0
        for i in range(0, len(self.data) - 2, 2):
            val = struct.unpack('>H', self.data[i:i+2])[0]
            if 50 <= val <= 500:
                nox_count += 1
        
        if nox_count > 100:
            findings['issues_found'].append({
                'severity': 'LOW',
                'component': 'NOX_SENSOR',
                'issue': 'NOx threshold values detected',
                'count': nox_count,
                'impact': 'Potential NOx sensor monitoring active',
                'recommendation': 'Disable NOx sensor monitoring if sensor removed'
            })
        
        findings['status'] = 'WARNING' if findings['issues_found'] else 'OK'
        print(f"[{'!' if findings['issues_found'] else '+'}] NOx Status: {findings['status']}")
        
        return findings
    
    def _find_zero_regions(self, min_length: int = 16) -> List[Tuple[int, int]]:
        """Find regions of consecutive zeros"""
        regions = []
        start = None
        length = 0
        
        for i, byte in enumerate(self.data):
            if byte == 0:
                if start is None:
                    start = i
                length += 1
            else:
                if start is not None and length >= min_length:
                    regions.append((start, length))
                start = None
                length = 0
        
        return regions
    
    def _find_sequential_patterns(self, min_val: int, max_val: int, min_length: int) -> List[Dict]:
        """Find sequential value patterns within a range"""
        patterns = []
        
        for i in range(0, len(self.data) - min_length):
            sequence = self.data[i:i+min_length]
            if all(min_val <= b <= max_val for b in sequence):
                patterns.append({
                    'offset': hex(i),
                    'length': min_length,
                    'values': list(sequence)
                })
        
        return patterns
    
    def generate_harmonization_report(self) -> Dict:
        """Generate comprehensive harmonization report"""
        print("\n" + "="*80)
        print("EMISSIONS SYSTEM HARMONIZATION ANALYSIS")
        print("="*80)
        
        report = {
            'metadata': {
                'filename': os.path.basename(self.filepath),
                'filesize': self.filesize,
                'analysis_date': datetime.now().isoformat(),
                'analyzer_version': '1.0.0'
            },
            'dpf_analysis': self.check_dpf_regeneration_logic(),
            'egr_analysis': self.check_egr_control_logic(),
            'throttle_analysis': self.check_throttle_valve_logic(),
            'lambda_analysis': self.check_lambda_sensor_logic(),
            'nox_analysis': self.check_nox_sensor_logic()
        }
        
        # Compile all issues
        all_issues = []
        for key in ['dpf_analysis', 'egr_analysis', 'throttle_analysis', 'lambda_analysis', 'nox_analysis']:
            all_issues.extend(report[key].get('issues_found', []))
        
        report['summary'] = {
            'total_issues': len(all_issues),
            'critical_issues': len([i for i in all_issues if i['severity'] == 'HIGH']),
            'medium_issues': len([i for i in all_issues if i['severity'] == 'MEDIUM']),
            'low_issues': len([i for i in all_issues if i['severity'] == 'LOW']),
            'overall_status': 'NEEDS_HARMONIZATION' if all_issues else 'OK'
        }
        
        # Print summary
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        print(f"Total Issues Found: {report['summary']['total_issues']}")
        print(f"  - Critical (HIGH): {report['summary']['critical_issues']}")
        print(f"  - Medium: {report['summary']['medium_issues']}")
        print(f"  - Low: {report['summary']['low_issues']}")
        print(f"\nOverall Status: {report['summary']['overall_status']}")
        print("="*80)
        
        # Print detailed issues
        if all_issues:
            print("\nDETAILED ISSUES:")
            print("-"*80)
            for idx, issue in enumerate(all_issues, 1):
                print(f"\n{idx}. [{issue['severity']}] {issue['component']}")
                print(f"   Issue: {issue['issue']}")
                print(f"   Impact: {issue['impact']}")
                print(f"   Recommendation: {issue['recommendation']}")
        
        return report
    
    def save_report(self, report: Dict, output_file: str = None):
        """Save report to JSON file"""
        if output_file is None:
            output_file = f"{os.path.basename(self.filepath)}_harmonization_report.json"
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n[+] Report saved to: {output_file}")
        return output_file


def main():
    """Main execution"""
    if len(sys.argv) < 2:
        print("ECU Emissions System Harmonizer")
        print("="*80)
        print("\nUsage: python emissions_harmonizer.py <ecu_file.bin>")
        print("\nExample:")
        print("  python emissions_harmonizer.py 3.95R_V3_ApexD_Kosthos_MASTER_DPF_OFF_NOCHK_P242FOFF-patched4plusVMAX300.bin")
        print("\nThis tool analyzes ECU calibration files for retained emissions control logic")
        print("when physical components (DPF, EGR, Throttle Valve) have been removed.")
        sys.exit(1)
    
    ecu_file = sys.argv[1]
    
    harmonizer = EmissionsHarmonizer(ecu_file)
    
    if not harmonizer.load_file():
        sys.exit(1)
    
    # Generate comprehensive report
    report = harmonizer.generate_harmonization_report()
    
    # Save report
    harmonizer.save_report(report)
    
    print("\n[+] Analysis complete!")
    
    # Exit with error code if issues found
    if report['summary']['total_issues'] > 0:
        print("\n[!] Harmonization required - issues detected")
        sys.exit(2)
    else:
        print("\n[+] No harmonization issues detected")
        sys.exit(0)


if __name__ == "__main__":
    main()
