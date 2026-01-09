#!/bin/bash

################################################################################
# ApexD Tuned File Analysis Script
# Complete workflow for analyzing ECU calibration files
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_header() {
    echo -e "${BLUE}================================================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================================================================================${NC}"
}

print_success() {
    echo -e "${GREEN}[+] $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}[!] $1${NC}"
}

print_error() {
    echo -e "${RED}[-] $1${NC}"
}

print_info() {
    echo -e "${BLUE}[*] $1${NC}"
}

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is required but not installed"
    exit 1
fi

print_success "Python 3 found: $(python3 --version)"

# File paths
APEXD_FILE="3.95R_V3_ApexD_Kosthos_MASTER_DPF_OFF_NOCHK_P242FOFF-patched4plusVMAX300.bin"
ORIGINAL_FILE="ALGARD_Q7_BTR_EDC16+CP34_V8_ORI"
REFERENCE_FILE="Q7_BTR_EDC16+CP34_V8_M&S_CAN_1ST_READ_MASTER_SW1037391528_UPG_SW_4L0910409_0040"

# Check if files exist
print_header "CHECKING FILE AVAILABILITY"

FILES_FOUND=0

if [ -f "$APEXD_FILE" ]; then
    print_success "ApexD tuned file found: $APEXD_FILE"
    FILES_FOUND=$((FILES_FOUND + 1))
else
    print_warning "ApexD tuned file not found: $APEXD_FILE"
fi

if [ -f "$ORIGINAL_FILE" ]; then
    print_success "Original file found: $ORIGINAL_FILE"
    FILES_FOUND=$((FILES_FOUND + 1))
else
    print_warning "Original file not found: $ORIGINAL_FILE"
fi

if [ -f "$REFERENCE_FILE" ]; then
    print_success "Reference file found: $REFERENCE_FILE"
    FILES_FOUND=$((FILES_FOUND + 1))
else
    print_warning "Reference file not found: $REFERENCE_FILE"
fi

if [ $FILES_FOUND -eq 0 ]; then
    print_error "No ECU files found in current directory"
    print_info "Please place the following files in the current directory:"
    print_info "  1. $APEXD_FILE"
    print_info "  2. $ORIGINAL_FILE"
    print_info "  3. $REFERENCE_FILE"
    exit 1
fi

# Create output directory
OUTPUT_DIR="analysis_results_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUTPUT_DIR"
print_success "Created output directory: $OUTPUT_DIR"

# Phase 1: Basic File Analysis
if [ -f "$APEXD_FILE" ]; then
    print_header "PHASE 1: BASIC FILE ANALYSIS"
    print_info "Analyzing ApexD tuned file structure..."
    
    python3 ecu_analyzer.py "$APEXD_FILE" > "$OUTPUT_DIR/basic_analysis.log" 2>&1
    
    if [ $? -eq 0 ]; then
        print_success "Basic analysis complete"
        # Move generated reports to output directory
        mv "${APEXD_FILE}_analysis.json" "$OUTPUT_DIR/" 2>/dev/null || true
    else
        print_warning "Basic analysis encountered issues (see log)"
    fi
fi

# Phase 2: Emissions System Harmonization Analysis
if [ -f "$APEXD_FILE" ]; then
    print_header "PHASE 2: EMISSIONS SYSTEM HARMONIZATION ANALYSIS"
    print_info "Checking for retained emissions control logic..."
    
    python3 emissions_harmonizer.py "$APEXD_FILE" > "$OUTPUT_DIR/harmonization_analysis.log" 2>&1
    
    HARMONIZATION_EXIT_CODE=$?
    
    if [ $HARMONIZATION_EXIT_CODE -eq 0 ]; then
        print_success "No harmonization issues detected"
    elif [ $HARMONIZATION_EXIT_CODE -eq 2 ]; then
        print_warning "Harmonization issues detected - review required"
    else
        print_error "Harmonization analysis failed"
    fi
    
    # Move generated reports to output directory
    mv "${APEXD_FILE}_harmonization_report.json" "$OUTPUT_DIR/" 2>/dev/null || true
fi

# Phase 3: File Comparison
if [ -f "$APEXD_FILE" ] && [ -f "$ORIGINAL_FILE" ]; then
    print_header "PHASE 3: FILE COMPARISON ANALYSIS"
    print_info "Comparing ApexD file with original..."
    
    if [ -f "$REFERENCE_FILE" ]; then
        python3 compare_ecu_files.py "$ORIGINAL_FILE" "$APEXD_FILE" "$REFERENCE_FILE" > "$OUTPUT_DIR/comparison_analysis.log" 2>&1
    else
        python3 compare_ecu_files.py "$ORIGINAL_FILE" "$APEXD_FILE" > "$OUTPUT_DIR/comparison_analysis.log" 2>&1
    fi
    
    if [ $? -eq 0 ]; then
        print_success "Comparison analysis complete"
        # Move generated reports to output directory
        mv comparison_report_*.json "$OUTPUT_DIR/" 2>/dev/null || true
    else
        print_warning "Comparison analysis encountered issues (see log)"
    fi
fi

# Phase 4: Generate Summary Report
print_header "PHASE 4: GENERATING SUMMARY REPORT"

SUMMARY_FILE="$OUTPUT_DIR/ANALYSIS_SUMMARY.txt"

cat > "$SUMMARY_FILE" << EOF
================================================================================
APEXD TUNED FILE ANALYSIS SUMMARY
================================================================================

Analysis Date: $(date)
Analyzer Version: 1.0.0

FILES ANALYZED:
---------------
ApexD Tuned File: $APEXD_FILE
Original File: $ORIGINAL_FILE
Reference File: $REFERENCE_FILE

ANALYSIS PHASES COMPLETED:
--------------------------
EOF

if [ -f "$OUTPUT_DIR/basic_analysis.log" ]; then
    echo "[✓] Phase 1: Basic File Analysis" >> "$SUMMARY_FILE"
else
    echo "[✗] Phase 1: Basic File Analysis - SKIPPED" >> "$SUMMARY_FILE"
fi

if [ -f "$OUTPUT_DIR/harmonization_analysis.log" ]; then
    echo "[✓] Phase 2: Emissions Harmonization Analysis" >> "$SUMMARY_FILE"
else
    echo "[✗] Phase 2: Emissions Harmonization Analysis - SKIPPED" >> "$SUMMARY_FILE"
fi

if [ -f "$OUTPUT_DIR/comparison_analysis.log" ]; then
    echo "[✓] Phase 3: File Comparison Analysis" >> "$SUMMARY_FILE"
else
    echo "[✗] Phase 3: File Comparison Analysis - SKIPPED" >> "$SUMMARY_FILE"
fi

cat >> "$SUMMARY_FILE" << EOF

OUTPUT FILES:
-------------
All analysis results have been saved to: $OUTPUT_DIR/

Key Files:
  - basic_analysis.log: Detailed file structure analysis
  - harmonization_analysis.log: Emissions system check results
  - comparison_analysis.log: File comparison results
  - *.json: Machine-readable analysis data

NEXT STEPS:
-----------
1. Review the harmonization analysis log for any critical issues
2. Check the comparison report to understand what was modified
3. Verify all emissions control systems are properly disabled
4. If issues found, apply recommended harmonization fixes
5. Re-run analysis after making corrections

RECOMMENDATIONS:
----------------
EOF

# Extract key findings from harmonization report if available
if [ -f "$OUTPUT_DIR/${APEXD_FILE}_harmonization_report.json" ]; then
    TOTAL_ISSUES=$(python3 -c "import json; data=json.load(open('$OUTPUT_DIR/${APEXD_FILE}_harmonization_report.json')); print(data['summary']['total_issues'])" 2>/dev/null || echo "N/A")
    CRITICAL_ISSUES=$(python3 -c "import json; data=json.load(open('$OUTPUT_DIR/${APEXD_FILE}_harmonization_report.json')); print(data['summary']['critical_issues'])" 2>/dev/null || echo "N/A")
    
    echo "Total Issues Found: $TOTAL_ISSUES" >> "$SUMMARY_FILE"
    echo "Critical Issues: $CRITICAL_ISSUES" >> "$SUMMARY_FILE"
    echo "" >> "$SUMMARY_FILE"
    
    if [ "$CRITICAL_ISSUES" != "0" ] && [ "$CRITICAL_ISSUES" != "N/A" ]; then
        echo "⚠️  CRITICAL: Harmonization required - emissions control logic still active" >> "$SUMMARY_FILE"
        echo "   Review harmonization_analysis.log for detailed recommendations" >> "$SUMMARY_FILE"
    else
        echo "✓ No critical harmonization issues detected" >> "$SUMMARY_FILE"
    fi
else
    echo "Harmonization report not available" >> "$SUMMARY_FILE"
fi

cat >> "$SUMMARY_FILE" << EOF

================================================================================
For detailed technical information, refer to: ECU_HARMONIZATION_GUIDE.md
================================================================================
EOF

print_success "Summary report generated: $SUMMARY_FILE"

# Display summary
print_header "ANALYSIS COMPLETE"
cat "$SUMMARY_FILE"

print_info ""
print_success "All analysis results saved to: $OUTPUT_DIR/"
print_info "Review the summary and detailed logs for complete findings"

exit 0
