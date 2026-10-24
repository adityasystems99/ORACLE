"""Audit runner executing OracleEvaluator and printing structured report."""

import asyncio
import json
import os
import sys
from pathlib import Path

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from eval.evaluator import OracleEvaluator

async def main():
    evaluator = OracleEvaluator()
    try:
        report = await evaluator.run_full_audit()
        print("\n" + "=" * 80)
        print("ORACLE END-TO-END AUDIT REPORT")
        print("=" * 80)
        print(json.dumps(report, indent=2))
        print("=" * 80)
        
        # Save report to eval/audit_results.json
        with open("eval/audit_results.json", "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print("Saved raw audit metrics to backend/eval/audit_results.json")
    finally:
        evaluator.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
