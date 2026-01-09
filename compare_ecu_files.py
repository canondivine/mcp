#!/usr/bin/env python3
"""
ECU File Comparison Tool
Compares original and modified ECU calibration files to identify changes
and verify completeness of emissions system removal
"""

import sys
import os
from typing import Dict, List, Tuple
import json
from datetime import datetime

class ECUFileComparator:
    """Compare two ECU calibration files"""
    
    def __init__(self, original_file: str, modified_file: str, reference_file: str = None):
        self.original_file = original_file
        self.modified_file = modified_file
        self.reference_file = reference_file
        self.original_data = bytearray()
        self.modified_data = bytearray()
        self.reference_data = bytearray() if reference_file else None
        
    def load_files(self) -> bool:
        """Load all files"""
        try:
            print("[*] Loading files...")
            
            with open(self.original_file, 'rb') as f:
                self.original_data = bytearray(f.read())
            print(f"[+] Loaded original: {self.original_file} ({len(self.original_data)} bytes)")
            
            with open(self.modified_file, 'rb') as f:
                self.modified_data = bytearray(f.read())
            print(f"[+] Loaded modified: {self.modified_file} ({len(self.modified_data)} bytes)")
            
            if self.reference_file:
                with open(self.reference_file, 'rb') as f:
                    self.reference_data = bytearray(f.read())
                print(f"[+] Loaded reference: {self.reference_file} ({len(self.reference_data)} bytes)")
            
            return True
        except Exception as e:
            print(f"[-] Error loading files: {e}")
            return False
    
    def verify_file_sizes(self) -> Dict:
        """Verify file sizes match"""
        print("\n[*] Verifying file sizes...")
        
        result = {
            'original_size': len(self.original_data),
            'modified_size': len(self.modified_data),
            'sizes_match': len(self.original_data) == len(self.modified_data),
            'size_difference': len(self.modified_data) - len(self.original_data)
        }
        
        if self.reference_data:
            result['reference_size'] = len(self.reference_data)
            result['reference_matches_original'] = len(self.reference_data) == len(self.original_data)
        
        if result['sizes_match']:
            print(f"[+] File sizes match: {result['original_size']} bytes")
        else:
            print(f"[!] File size mismatch: Original={result['original_size']}, Modified={result['modified_size']}")
            print(f"[!] Difference: {result['size_difference']} bytes")
        
        return result
    
    def find_differences(self) -> Dict:
        """Find all byte differences between files"""
        print("\n[*] Analyzing byte-level differences...")
        
        if len(self.original_data) != len(self.modified_data):
            print("[!] Cannot compare - file sizes differ")
            return {'error': 'File size mismatch'}
        
        differences = []
        diff_regions = []
        in_diff_region = False
        region_start = 0
        region_original = bytearray()
        region_modified = bytearray()
        
        for i in range(len(self.original_data)):
            if self.original_data[i] != self.modified_data[i]:
                differences.append(i)
                
                if not in_diff_region:
                    in_diff_region = True
                    region_start = i
                    region_original = bytearray()
                    region_modified = bytearray()
                
                region_original.append(self.original_data[i])
                region_modified.append(self.modified_data[i])
            else:
                if in_diff_region:
                    # End of diff region
                    diff_regions.append({
                        'start_offset': hex(region_start),
                        'end_offset': hex(i - 1),
                        'size': i - region_start,
                        'original_bytes': region_original.hex()[:200],  # Limit display
                        'modified_bytes': region_modified.hex()[:200],
                        'original_sample': list(region_original[:16]),
                        'modified_sample': list(region_modified[:16])
                    })
                    in_diff_region = False
        
        # Handle case where file ends in diff region
        if in_diff_region:
            diff_regions.append({
                'start_offset': hex(region_start),
                'end_offset': hex(len(self.original_data) - 1),
                'size': len(self.original_data) - region_start,
                'original_bytes': region_original.hex()[:200],
                'modified_bytes': region_modified.hex()[:200],
                'original_sample': list(region_original[:16]),
                'modified_sample': list(region_modified[:16])
            })
        
        total_diff_bytes = len(differences)
        modification_percentage = (total_diff_bytes / len(self.original_data)) * 100
        
        print(f"[+] Total different bytes: {total_diff_bytes}")
        print(f"[+] Modification percentage: {modification_percentage:.2f}%")
        print(f"[+] Number of diff regions: {len(diff_regions)}")
        
        return {
            'total_differences': total_diff_bytes,
            'modification_percentage': modification_percentage,
            'diff_regions': diff_regions,
            'diff_region_count': len(diff_regions)
        }
    
    def analyze_modification_patterns(self, diff_data: Dict) -> Dict:
        """Analyze patterns in modifications"""
        print("\n[*] Analyzing modification patterns...")
        
        patterns = {
            'zeroed_regions': [],
            'maxed_regions': [],
            'inverted_regions': [],
            'scaled_regions': []
        }
        
        for region in diff_data.get('diff_regions', []):
            original_sample = region.get('original_sample', [])
            modified_sample = region.get('modified_sample', [])
            
            if not original_sample or not modified_sample:
                continue
            
            # Check if region was zeroed
            if all(b == 0 for b in modified_sample):
                patterns['zeroed_regions'].append({
                    'offset': region['start_offset'],
                    'size': region['size'],
                    'type': 'ZEROED',
                    'likely_purpose': 'Disabled function or map'
                })
            
            # Check if region was maxed (all 0xFF)
            elif all(b == 0xFF for b in modified_sample):
                patterns['maxed_regions'].append({
                    'offset': region['start_offset'],
                    'size': region['size'],
                    'type': 'MAXED',
                    'likely_purpose': 'Disabled threshold or limiter'
                })
            
            # Check if values were inverted
            elif len(original_sample) == len(modified_sample):
                inverted = all(
                    (original_sample[i] ^ 0xFF) == modified_sample[i]
                    for i in range(len(original_sample))
                )
                if inverted:
                    patterns['inverted_regions'].append({
                        'offset': region['start_offset'],
                        'size': region['size'],
                        'type': 'INVERTED',
                        'likely_purpose': 'Bitwise inversion'
                    })
        
        print(f"[+] Zeroed regions: {len(patterns['zeroed_regions'])}")
        print(f"[+] Maxed regions: {len(patterns['maxed_regions'])}")
        print(f"[+] Inverted regions: {len(patterns['inverted_regions'])}")
        
        return patterns
    
    def check_emissions_modifications(self) -> Dict:
        """Check if emissions-related modifications are complete"""
        print("\n[*] Checking emissions system modifications...")
        
        checks = {
            'dpf_disabled': False,
            'egr_disabled': False,
            'throttle_disabled': False,
            'details': []
        }
        
        # Count zero bytes in modified file (indicator of disabled functions)
        zero_count_original = sum(1 for b in self.original_data if b == 0)
        zero_count_modified = sum(1 for b in self.modified_data if b == 0)
        zero_increase = zero_count_modified - zero_count_original
        
        print(f"[+] Zero bytes in original: {zero_count_original}")
        print(f"[+] Zero bytes in modified: {zero_count_modified}")
        print(f"[+] Zero byte increase: {zero_increase}")
        
        if zero_increase > 1000:
            checks['details'].append({
                'check': 'Zero byte increase',
                'result': 'PASS',
                'value': zero_increase,
                'interpretation': 'Significant zeroing suggests emissions functions disabled'
            })
            checks['dpf_disabled'] = True
            checks['egr_disabled'] = True
        else:
            checks['details'].append({
                'check': 'Zero byte increase',
                'result': 'WARNING',
                'value': zero_increase,
                'interpretation': 'Limited zeroing - emissions functions may still be active'
            })
        
        # Count 0xFF bytes (max values - often used to disable thresholds)
        ff_count_original = sum(1 for b in self.original_data if b == 0xFF)
        ff_count_modified = sum(1 for b in self.modified_data if b == 0xFF)
        ff_increase = ff_count_modified - ff_count_original
        
        print(f"[+] 0xFF bytes in original: {ff_count_original}")
        print(f"[+] 0xFF bytes in modified: {ff_count_modified}")
        print(f"[+] 0xFF byte increase: {ff_increase}")
        
        if ff_increase > 500:
            checks['details'].append({
                'check': '0xFF byte increase',
                'result': 'PASS',
                'value': ff_increase,
                'interpretation': 'Thresholds likely disabled'
            })
        
        return checks
    
    def compare_with_reference(self) -> Dict:
        """Compare modified file with reference file"""
        if not self.reference_data:
            return {'error': 'No reference file provided'}
        
        print("\n[*] Comparing with reference file...")
        
        if len(self.reference_data) != len(self.modified_data):
            print("[!] Reference file size mismatch")
            return {'error': 'Reference file size mismatch'}
        
        differences = []
        for i in range(len(self.reference_data)):
            if self.reference_data[i] != self.modified_data[i]:
                differences.append(i)
        
        similarity_percentage = ((len(self.reference_data) - len(differences)) / len(self.reference_data)) * 100
        
        print(f"[+] Similarity with reference: {similarity_percentage:.2f}%")
        print(f"[+] Different bytes: {len(differences)}")
        
        return {
            'similarity_percentage': similarity_percentage,
            'different_bytes': len(differences),
            'is_similar': similarity_percentage > 95.0
        }
    
    def generate_comparison_report(self) -> Dict:
        """Generate comprehensive comparison report"""
        print("\n" + "="*80)
        print("ECU FILE COMPARISON REPORT")
        print("="*80)
        
        report = {
            'metadata': {
                'original_file': os.path.basename(self.original_file),
                'modified_file': os.path.basename(self.modified_file),
                'reference_file': os.path.basename(self.reference_file) if self.reference_file else None,
                'analysis_date': datetime.now().isoformat(),
                'analyzer_version': '1.0.0'
            },
            'file_sizes': self.verify_file_sizes(),
            'differences': self.find_differences(),
            'emissions_checks': self.check_emissions_modifications()
        }
        
        # Add modification patterns
        if 'error' not in report['differences']:
            report['modification_patterns'] = self.analyze_modification_patterns(report['differences'])
        
        # Add reference comparison if available
        if self.reference_data:
            report['reference_comparison'] = self.compare_with_reference()
        
        # Generate summary
        report['summary'] = self._generate_summary(report)
        
        return report
    
    def _generate_summary(self, report: Dict) -> Dict:
        """Generate summary of findings"""
        summary = {
            'modification_level': 'UNKNOWN',
            'emissions_status': 'UNKNOWN',
            'recommendations': []
        }
        
        mod_pct = report['differences'].get('modification_percentage', 0)
        
        if mod_pct < 1:
            summary['modification_level'] = 'MINIMAL'
            summary['recommendations'].append('Very few modifications detected - verify emissions systems are properly disabled')
        elif mod_pct < 5:
            summary['modification_level'] = 'MODERATE'
            summary['recommendations'].append('Moderate modifications detected - review emissions system status')
        elif mod_pct < 15:
            summary['modification_level'] = 'SUBSTANTIAL'
            summary['recommendations'].append('Substantial modifications detected - likely emissions delete performed')
        else:
            summary['modification_level'] = 'EXTENSIVE'
            summary['recommendations'].append('Extensive modifications detected - comprehensive tune applied')
        
        # Check emissions status
        emissions = report.get('emissions_checks', {})
        if emissions.get('dpf_disabled') and emissions.get('egr_disabled'):
            summary['emissions_status'] = 'LIKELY_DISABLED'
        else:
            summary['emissions_status'] = 'UNCERTAIN'
            summary['recommendations'].append('Run emissions harmonization analysis to verify complete disabling')
        
        return summary
    
    def save_report(self, report: Dict, output_file: str = None):
        """Save comparison report"""
        if output_file is None:
            output_file = f"comparison_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n[+] Report saved to: {output_file}")
        return output_file
    
    def print_summary(self, report: Dict):
        """Print summary to console"""
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        
        summary = report.get('summary', {})
        print(f"Modification Level: {summary.get('modification_level', 'UNKNOWN')}")
        print(f"Emissions Status: {summary.get('emissions_status', 'UNKNOWN')}")
        
        if summary.get('recommendations'):
            print("\nRecommendations:")
            for rec in summary['recommendations']:
                print(f"  - {rec}")
        
        print("="*80)


def main():
    """Main execution"""
    if len(sys.argv) < 3:
        print("ECU File Comparison Tool")
        print("="*80)
        print("\nUsage: python compare_ecu_files.py <original.bin> <modified.bin> [reference.bin]")
        print("\nExample:")
        print("  python compare_ecu_files.py \\")
        print("    Q7_BTR_EDC16+CP34_V8_ORI \\")
        print("    3.95R_V3_ApexD_Kosthos_MASTER_DPF_OFF_NOCHK_P242FOFF-patched4plusVMAX300.bin \\")
        print("    Q7_BTR_EDC16+CP34_V8_M&S_CAN_1ST_READ_MASTER_SW1037391528_UPG_SW_4L0910409_0040")
        print("\nThis tool compares ECU calibration files to identify modifications")
        print("and verify emissions system removal completeness.")
        sys.exit(1)
    
    original_file = sys.argv[1]
    modified_file = sys.argv[2]
    reference_file = sys.argv[3] if len(sys.argv) > 3 else None
    
    comparator = ECUFileComparator(original_file, modified_file, reference_file)
    
    if not comparator.load_files():
        sys.exit(1)
    
    # Generate report
    report = comparator.generate_comparison_report()
    
    # Print summary
    comparator.print_summary(report)
    
    # Save report
    comparator.save_report(report)
    
    print("\n[+] Comparison complete!")


if __name__ == "__main__":
    main()
