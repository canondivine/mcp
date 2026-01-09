# ECU Calibration Analysis Tools

## Overview

This toolkit provides comprehensive analysis capabilities for ECU calibration files, specifically designed to identify and verify emissions system modifications (DPF, EGR, Throttle Valve removal) and ensure proper harmonization between ECU software and physical hardware configuration.

## Tools Included

### 1. **ecu_analyzer.py**
Basic ECU calibration file analyzer that examines file structure, identifies calibration maps, and extracts key parameters.

**Features:**
- File integrity verification (checksums)
- Calibration map detection (2D/3D maps)
- Fuel system analysis
- Torque limiter identification
- Pattern recognition for common ECU structures

**Usage:**
```bash
python3 ecu_analyzer.py <ecu_file.bin>
```

**Example:**
```bash
python3 ecu_analyzer.py 3.95R_V3_ApexD_Kosthos_MASTER_DPF_OFF_NOCHK_P242FOFF-patched4plusVMAX300.bin
```

**Output:**
- Console output with analysis summary
- JSON report: `<filename>_analysis.json`

---

### 2. **emissions_harmonizer.py**
Advanced emissions system harmonization analyzer that identifies retained control logic for physically removed components.

**Features:**
- DPF regeneration logic detection
- EGR valve control analysis
- Throttle valve modulation detection
- Lambda sensor target verification
- NOx sensor logic identification
- Severity-based issue reporting

**Usage:**
```bash
python3 emissions_harmonizer.py <ecu_file.bin>
```

**Example:**
```bash
python3 emissions_harmonizer.py 3.95R_V3_ApexD_Kosthos_MASTER_DPF_OFF_NOCHK_P242FOFF-patched4plusVMAX300.bin
```

**Output:**
- Console output with detailed findings
- JSON report: `<filename>_harmonization_report.json`
- Exit code 0: No issues found
- Exit code 2: Harmonization required

**Checks Performed:**
- ✓ DPF regeneration temperature thresholds
- ✓ DPF pressure differential monitoring
- ✓ EGR position command maps
- ✓ EGR torque compensation tables
- ✓ Throttle valve position maps
- ✓ Throttle modulation sequences
- ✓ Lambda sensor targets (rich mixture detection)
- ✓ NOx sensor monitoring

---

### 3. **compare_ecu_files.py**
File comparison tool that identifies all modifications between original and tuned calibration files.

**Features:**
- Byte-level difference analysis
- Modification region identification
- Pattern recognition (zeroed, maxed, inverted regions)
- Emissions modification verification
- Reference file comparison
- Modification percentage calculation

**Usage:**
```bash
python3 compare_ecu_files.py <original.bin> <modified.bin> [reference.bin]
```

**Example:**
```bash
python3 compare_ecu_files.py \
  ALGARD_Q7_BTR_EDC16+CP34_V8_ORI \
  3.95R_V3_ApexD_Kosthos_MASTER_DPF_OFF_NOCHK_P242FOFF-patched4plusVMAX300.bin \
  Q7_BTR_EDC16+CP34_V8_M&S_CAN_1ST_READ_MASTER_SW1037391528_UPG_SW_4L0910409_0040
```

**Output:**
- Console output with comparison summary
- JSON report: `comparison_report_<timestamp>.json`

---

### 4. **analyze_apexd_tuned_file.sh**
Master orchestration script that runs complete analysis workflow.

**Features:**
- Automated multi-phase analysis
- File availability checking
- Organized output directory structure
- Comprehensive summary report generation
- Color-coded console output

**Usage:**
```bash
chmod +x analyze_apexd_tuned_file.sh
./analyze_apexd_tuned_file.sh
```

**Requirements:**
Place the following files in the same directory:
- `3.95R_V3_ApexD_Kosthos_MASTER_DPF_OFF_NOCHK_P242FOFF-patched4plusVMAX300.bin`
- `ALGARD_Q7_BTR_EDC16+CP34_V8_ORI`
- `Q7_BTR_EDC16+CP34_V8_M&S_CAN_1ST_READ_MASTER_SW1037391528_UPG_SW_4L0910409_0040`

**Output:**
Creates timestamped directory: `analysis_results_YYYYMMDD_HHMMSS/`
- `basic_analysis.log`
- `harmonization_analysis.log`
- `comparison_analysis.log`
- `ANALYSIS_SUMMARY.txt`
- Various JSON reports

---

## Quick Start Guide

### Step 1: Prepare Files

Place your ECU calibration files in the working directory:

```bash
ls -lh
# Should show:
# 3.95R_V3_ApexD_Kosthos_MASTER_DPF_OFF_NOCHK_P242FOFF-patched4plusVMAX300.bin
# ALGARD_Q7_BTR_EDC16+CP34_V8_ORI
# Q7_BTR_EDC16+CP34_V8_M&S_CAN_1ST_READ_MASTER_SW1037391528_UPG_SW_4L0910409_0040
```

### Step 2: Run Complete Analysis

```bash
chmod +x analyze_apexd_tuned_file.sh
./analyze_apexd_tuned_file.sh
```

### Step 3: Review Results

```bash
cd analysis_results_*/
cat ANALYSIS_SUMMARY.txt
```

### Step 4: Examine Detailed Reports

```bash
# View harmonization issues
cat harmonization_analysis.log

# View file comparison
cat comparison_analysis.log

# View JSON data
cat *_harmonization_report.json | python3 -m json.tool
```

---

## Understanding the Output

### Harmonization Report Structure

```json
{
  "metadata": {
    "filename": "...",
    "filesize": 1048576,
    "analysis_date": "2026-01-09T..."
  },
  "dpf_analysis": {
    "status": "CRITICAL",
    "issues_found": [
      {
        "severity": "HIGH",
        "component": "DPF",
        "issue": "Active regeneration temperature thresholds detected",
        "impact": "ECU may attempt DPF regeneration...",
        "recommendation": "Set all DPF regeneration temperature thresholds to 0..."
      }
    ]
  },
  "summary": {
    "total_issues": 5,
    "critical_issues": 2,
    "overall_status": "NEEDS_HARMONIZATION"
  }
}
```

### Issue Severity Levels

- **HIGH (Critical)**: Must be fixed - causes operational problems
  - Active DPF regeneration logic
  - EGR valve control attempts
  - Throttle valve modulation

- **MEDIUM**: Should be fixed - causes performance/efficiency issues
  - EGR torque compensation
  - Throttle modulation sequences
  - Rich lambda targets

- **LOW**: Recommended to fix - minor issues
  - NOx sensor monitoring
  - Sensor error codes

---

## Interpretation Guide

### DPF Analysis Results

**Status: OK**
- No regeneration temperature thresholds detected
- DPF logic properly disabled
- ✓ No action required

**Status: CRITICAL**
- Active regeneration thresholds found
- ECU will attempt regeneration cycles
- ⚠️ Harmonization required

### EGR Analysis Results

**Status: OK**
- All EGR position maps at 0%
- Torque compensation tables zeroed
- ✓ No action required

**Status: CRITICAL**
- Non-zero EGR position commands detected
- Torque compensation active
- ⚠️ Harmonization required

### Throttle Analysis Results

**Status: OK**
- All throttle position maps at 100%
- No modulation sequences detected
- ✓ No action required

**Status: CRITICAL**
- Throttle modulation detected
- Position maps not at 100%
- ⚠️ Harmonization required

---

## Troubleshooting

### Issue: "File not found"
**Solution:** Ensure ECU files are in the current directory with exact filenames

### Issue: "Python 3 not found"
**Solution:** Install Python 3:
```bash
# Amazon Linux 2023
sudo dnf install python3

# Ubuntu/Debian
sudo apt install python3
```

### Issue: "Permission denied"
**Solution:** Make scripts executable:
```bash
chmod +x analyze_apexd_tuned_file.sh
```

### Issue: "File size mismatch"
**Solution:** Verify files are not corrupted:
```bash
md5sum *.bin
```

---

## Advanced Usage

### Analyze Single File

```bash
# Quick harmonization check
python3 emissions_harmonizer.py tuned_file.bin

# Detailed structure analysis
python3 ecu_analyzer.py tuned_file.bin
```

### Compare Two Files Only

```bash
python3 compare_ecu_files.py original.bin modified.bin
```

### Batch Analysis

```bash
# Analyze multiple files
for file in *.bin; do
    echo "Analyzing $file..."
    python3 emissions_harmonizer.py "$file"
done
```

---

## Technical Reference

### File Formats Supported
- Binary ECU calibration files (.bin)
- EDC16 ECU format
- Bosch ECU formats
- Generic binary calibration files

### Detection Methods

**Pattern Matching:**
- Byte sequence recognition
- Value range analysis
- Sequential pattern detection

**Statistical Analysis:**
- Zero byte counting
- Max value (0xFF) counting
- Modification percentage calculation

**Contextual Analysis:**
- Surrounding byte context
- Map structure recognition
- Axis value detection

---

## Safety and Legal Notices

⚠️ **IMPORTANT DISCLAIMERS:**

1. **Off-Road Use Only**: These tools are intended for off-road and racing applications only
2. **Legal Compliance**: Emissions equipment removal may be illegal for road use in many jurisdictions
3. **Professional Use**: Intended for professional tuners and automotive engineers
4. **No Warranty**: Tools provided as-is without warranty
5. **Backup Required**: Always maintain backup of original calibration
6. **Testing Required**: Thoroughly test modifications in controlled environment

---

## Support and Documentation

### Additional Resources

- **ECU_HARMONIZATION_GUIDE.md**: Comprehensive technical guide
- **Tool source code**: Fully commented Python scripts
- **Example outputs**: Sample analysis reports included

### Getting Help

1. Review the ECU_HARMONIZATION_GUIDE.md for technical details
2. Check tool output logs for specific error messages
3. Verify file integrity with checksums
4. Ensure Python 3.6+ is installed

---

## Version History

**Version 1.0.0** (January 9, 2026)
- Initial release
- Basic file analysis
- Emissions harmonization detection
- File comparison capabilities
- Automated workflow script

---

## Credits

**Developed by:** ECU Analysis System  
**Date:** January 9, 2026  
**Purpose:** Emissions system harmonization verification  
**License:** Professional use only

---

## Quick Reference Commands

```bash
# Complete analysis workflow
./analyze_apexd_tuned_file.sh

# Individual tool usage
python3 ecu_analyzer.py <file.bin>
python3 emissions_harmonizer.py <file.bin>
python3 compare_ecu_files.py <original.bin> <modified.bin>

# View results
cat analysis_results_*/ANALYSIS_SUMMARY.txt
cat analysis_results_*/harmonization_analysis.log

# Check for critical issues
grep -i "critical" analysis_results_*/harmonization_analysis.log
grep -i "high" analysis_results_*/harmonization_analysis.log
```

---

**End of Documentation**
