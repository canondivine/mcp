#!/usr/bin/env python3
"""
ECU Calibration File Analyzer
Analyzes ECU binary files for emissions system calibration and harmonization
Focuses on DPF, EGR, and throttle valve control systems
"""

import struct
import sys
import os
from typing import Dict, List, Tuple, Optional
import json

class ECUCalibrationAnalyzer:
    """Analyzer for ECU calibration binary files"""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.filesize = 0
        self.data = bytearray()
        self.analysis_results = {}
        
    def load_file(self) -> bool:
        """Load the binary file into memory"""
        try:
            with open(self.filepath, 'rb') as f:
                self.data = bytearray(f.read())
            self.filesize = len(self.data)
            print(f"[+] Loaded file: {self.filepath}")
            print(f"[+] File size: {self.filesize} bytes ({self.filesize / 1024:.2f} KB)")
            return True
        except Exception as e:
            print(f"[-] Error loading file: {e}")
            return False
    
    def calculate_checksum(self) -> Dict[str, str]:
        """Calculate various checksums for the file"""
        import hashlib
        
        checksums = {
            'md5': hashlib.md5(self.data).hexdigest(),
            'sha1': hashlib.sha1(self.data).hexdigest(),
            'sha256': hashlib.sha256(self.data).hexdigest()
        }
        return checksums
    
    def find_pattern(self, pattern: bytes, description: str = "") -> List[int]:
        """Find all occurrences of a byte pattern"""
        positions = []
        start = 0
        while True:
            pos = self.data.find(pattern, start)
            if pos == -1:
                break
            positions.append(pos)
            start = pos + 1
        
        if positions and description:
            print(f"[+] Found {len(positions)} occurrence(s) of {description} at: {[hex(p) for p in positions[:10]]}")
        return positions
    
    def analyze_emissions_signatures(self) -> Dict:
        """Analyze emissions-related signatures and patterns"""
        print("\n[*] Analyzing emissions system signatures...")
        
        emissions_data = {
            'dpf_patterns': [],
            'egr_patterns': [],
            'throttle_patterns': [],
            'lambda_patterns': [],
            'nox_patterns': []
        }
        
        # Common DPF-related patterns (hex sequences often found in DPF logic)
        dpf_signatures = [
            (b'\x00\x00\x00\x00\x00\x00\x00\x00', "DPF disabled signature (8 zeros)"),
            (b'\xFF\xFF\xFF\xFF', "DPF max value signature"),
            (b'\x00\x64', "DPF percentage value (100)"),
        ]
        
        # EGR-related patterns
        egr_signatures = [
            (b'\x00\x00\x00\x00', "EGR disabled signature (4 zeros)"),
            (b'\xFF\xFF', "EGR max value"),
        ]
        
        # Throttle valve patterns
        throttle_signatures = [
            (b'\x00\x00', "Throttle closed signature"),
            (b'\x64\x00', "Throttle 100% signature"),
        ]
        
        for pattern, desc in dpf_signatures:
            positions = self.find_pattern(pattern, f"DPF: {desc}")
            emissions_data['dpf_patterns'].append({
                'description': desc,
                'count': len(positions),
                'positions': positions[:20]  # Limit to first 20
            })
        
        for pattern, desc in egr_signatures:
            positions = self.find_pattern(pattern, f"EGR: {desc}")
            emissions_data['egr_patterns'].append({
                'description': desc,
                'count': len(positions),
                'positions': positions[:20]
            })
        
        for pattern, desc in throttle_signatures:
            positions = self.find_pattern(pattern, f"Throttle: {desc}")
            emissions_data['throttle_patterns'].append({
                'description': desc,
                'count': len(positions),
                'positions': positions[:20]
            })
        
        return emissions_data
    
    def analyze_calibration_maps(self) -> Dict:
        """Analyze potential calibration map structures"""
        print("\n[*] Analyzing calibration map structures...")
        
        maps_data = {
            'potential_2d_maps': [],
            'potential_3d_maps': [],
            'axis_candidates': []
        }
        
        # Look for common map axis patterns (sequential values)
        # Common RPM axis values: 500, 1000, 1500, 2000, 2500, 3000, etc.
        rpm_patterns = []
        for i in range(0, len(self.data) - 20, 2):
            # Check for sequential 16-bit values that could be RPM axis
            values = []
            for j in range(10):
                if i + j*2 + 1 < len(self.data):
                    val = struct.unpack('>H', self.data[i+j*2:i+j*2+2])[0]
                    values.append(val)
            
            # Check if values are sequential and in reasonable RPM range
            if len(values) == 10:
                if all(500 <= v <= 6000 for v in values):
                    if all(values[i] < values[i+1] for i in range(len(values)-1)):
                        rpm_patterns.append({
                            'offset': hex(i),
                            'values': values
                        })
        
        if rpm_patterns:
            print(f"[+] Found {len(rpm_patterns)} potential RPM axis patterns")
            maps_data['axis_candidates'] = rpm_patterns[:10]  # Limit output
        
        return maps_data
    
    def analyze_fuel_maps(self) -> Dict:
        """Analyze fuel-related calibration data"""
        print("\n[*] Analyzing fuel system calibration...")
        
        fuel_data = {
            'injection_timing_candidates': [],
            'fuel_pressure_candidates': [],
            'rail_pressure_candidates': []
        }
        
        # Look for common fuel pressure values (bar * 10)
        # Common rail pressure: 200-2000 bar (stored as 2000-20000)
        for i in range(0, len(self.data) - 2, 2):
            val = struct.unpack('>H', self.data[i:i+2])[0]
            if 2000 <= val <= 20000:
                fuel_data['rail_pressure_candidates'].append({
                    'offset': hex(i),
                    'value': val,
                    'bar': val / 10
                })
        
        print(f"[+] Found {len(fuel_data['rail_pressure_candidates'])} potential rail pressure values")
        
        return fuel_data
    
    def analyze_torque_limiters(self) -> Dict:
        """Analyze torque limiter maps"""
        print("\n[*] Analyzing torque limiter structures...")
        
        torque_data = {
            'potential_limiters': [],
            'max_torque_values': []
        }
        
        # Look for torque values (typically 0-1000 Nm, stored in various formats)
        for i in range(0, len(self.data) - 2, 2):
            val = struct.unpack('>H', self.data[i:i+2])[0]
            if 100 <= val <= 1000:  # Reasonable torque range for V8 diesel
                torque_data['potential_limiters'].append({
                    'offset': hex(i),
                    'value': val
                })
        
        print(f"[+] Found {len(torque_data['potential_limiters'])} potential torque values")
        
        return torque_data
    
    def compare_with_original(self, original_file: str) -> Dict:
        """Compare current file with original to identify modifications"""
        print(f"\n[*] Comparing with original file: {original_file}")
        
        try:
            with open(original_file, 'rb') as f:
                original_data = bytearray(f.read())
        except Exception as e:
            print(f"[-] Error loading original file: {e}")
            return {}
        
        if len(original_data) != len(self.data):
            print(f"[!] File size mismatch: Original={len(original_data)}, Current={len(self.data)}")
            return {'error': 'File size mismatch'}
        
        differences = []
        diff_regions = []
        in_diff_region = False
        region_start = 0
        
        for i in range(len(self.data)):
            if self.data[i] != original_data[i]:
                if not in_diff_region:
                    in_diff_region = True
                    region_start = i
            else:
                if in_diff_region:
                    in_diff_region = False
                    diff_regions.append({
                        'start': hex(region_start),
                        'end': hex(i-1),
                        'size': i - region_start,
                        'original_bytes': original_data[region_start:i].hex()[:100],
                        'modified_bytes': self.data[region_start:i].hex()[:100]
                    })
        
        print(f"[+] Found {len(diff_regions)} modified regions")
        
        return {
            'total_differences': len([i for i in range(len(self.data)) if self.data[i] != original_data[i]]),
            'diff_regions': diff_regions[:50],  # Limit to first 50 regions
            'modification_percentage': (len([i for i in range(len(self.data)) if self.data[i] != original_data[i]]) / len(self.data)) * 100
        }
    
    def generate_report(self, output_file: str = "ecu_analysis_report.json"):
        """Generate comprehensive analysis report"""
        print("\n[*] Generating analysis report...")
        
        report = {
            'file_info': {
                'filename': os.path.basename(self.filepath),
                'size_bytes': self.filesize,
                'size_kb': self.filesize / 1024,
                'checksums': self.calculate_checksum()
            },
            'emissions_analysis': self.analyze_emissions_signatures(),
            'calibration_maps': self.analyze_calibration_maps(),
            'fuel_system': self.analyze_fuel_maps(),
            'torque_limiters': self.analyze_torque_limiters()
        }
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"[+] Report saved to: {output_file}")
        return report
    
    def print_summary(self):
        """Print analysis summary"""
        print("\n" + "="*80)
        print("ECU CALIBRATION ANALYSIS SUMMARY")
        print("="*80)
        print(f"File: {self.filepath}")
        print(f"Size: {self.filesize} bytes ({self.filesize / 1024:.2f} KB)")
        print(f"MD5: {self.calculate_checksum()['md5']}")
        print("="*80)


def main():
    """Main execution function"""
    if len(sys.argv) < 2:
        print("Usage: python ecu_analyzer.py <ecu_file.bin> [original_file.bin]")
        print("\nExample:")
        print("  python ecu_analyzer.py 3.95R_V3_ApexD_Kosthos_MASTER_DPF_OFF_NOCHK_P242FOFF-patched4plusVMAX300.bin")
        print("  python ecu_analyzer.py tuned.bin original.bin")
        sys.exit(1)
    
    tuned_file = sys.argv[1]
    original_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Analyze tuned file
    analyzer = ECUCalibrationAnalyzer(tuned_file)
    
    if not analyzer.load_file():
        sys.exit(1)
    
    analyzer.print_summary()
    
    # Generate report
    report = analyzer.generate_report(f"{os.path.basename(tuned_file)}_analysis.json")
    
    # Compare with original if provided
    if original_file:
        comparison = analyzer.compare_with_original(original_file)
        if comparison:
            print(f"\n[+] Modification percentage: {comparison.get('modification_percentage', 0):.2f}%")
            print(f"[+] Total modified bytes: {comparison.get('total_differences', 0)}")
            print(f"[+] Modified regions: {len(comparison.get('diff_regions', []))}")
            
            # Save comparison report
            with open(f"{os.path.basename(tuned_file)}_comparison.json", 'w') as f:
                json.dump(comparison, f, indent=2)
            print(f"[+] Comparison report saved")
    
    print("\n[+] Analysis complete!")


if __name__ == "__main__":
    main()
