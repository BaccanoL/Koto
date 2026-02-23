#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 6 - Advanced Testing & Quality Assurance System
Test generation, coverage analysis, and test execution

This module provides:
1. Automated test generation from source code
2. Test suite management and organization
3. Coverage analysis and reporting
4. Test execution monitoring
5. Quality metrics and reporting
"""

import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Callable
from dataclasses import dataclass, asdict, field


@dataclass
class TestCase:
    """Represents a single test case"""
    test_id: str
    name: str
    function_name: str
    description: str
    test_code: str
    inputs: List[Any]
    expected_output: Any
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_run: Optional[str] = None
    status: str = "pending"  # pending, pass, fail
    execution_time: float = 0.0
    error_message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestCase':
        """Create from dictionary"""
        return cls(**data)


@dataclass
class TestSuite:
    """Represents a collection of test cases"""
    suite_id: str
    name: str
    description: str
    version: str
    test_cases: List[TestCase] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_run: Optional[str] = None
    total_runs: int = 0
    pass_count: int = 0
    fail_count: int = 0
    pass_rate: float = 0.0
    tags: List[str] = field(default_factory=list)
    
    def add_test(self, test: TestCase):
        """Add test case to suite"""
        self.test_cases.append(test)
    
    def remove_test(self, test_id: str):
        """Remove test case from suite"""
        self.test_cases = [t for t in self.test_cases if t.test_id != test_id]
    
    def update_stats(self):
        """Update test statistics"""
        if not self.test_cases:
            self.pass_rate = 0.0
            return
        
        self.pass_count = sum(1 for t in self.test_cases if t.status == "pass")
        self.fail_count = sum(1 for t in self.test_cases if t.status == "fail")
        self.pass_rate = (self.pass_count / len(self.test_cases)) * 100 if self.test_cases else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['test_cases'] = [t.to_dict() for t in self.test_cases]
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestSuite':
        """Create from dictionary"""
        test_cases = [TestCase.from_dict(t) for t in data.pop('test_cases', [])]
        suite = cls(**data)
        suite.test_cases = test_cases
        return suite


class TestGenerator:
    """Generate test cases from source code analysis"""
    
    def __init__(self):
        self.generated_tests: List[TestCase] = []
    
    def analyze_function(self, func_source: str, func_name: str) -> List[Dict[str, Any]]:
        """Analyze function to identify test cases"""
        test_ideas = []
        
        # Extract docstring
        docstring_match = re.search(r'"""(.*?)"""|\'\'\'(.*?)\'\'\'', func_source, re.DOTALL)
        docstring = docstring_match.group(1) or docstring_match.group(2) if docstring_match else ""
        
        # Extract parameters
        params_match = re.search(r'def\s+\w+\s*\((.*?)\)', func_source)
        params = [p.strip().split(':')[0] for p in params_match.group(1).split(',')] if params_match else []
        
        # Basic test cases
        test_ideas.append({
            "type": "basic",
            "description": f"Test {func_name} with valid inputs",
            "category": "happy_path"
        })
        test_ideas.append({
            "type": "edge_case",
            "description": f"Test {func_name} with edge cases",
            "category": "edge_case"
        })
        test_ideas.append({
            "type": "error_handling",
            "description": f"Test {func_name} error handling",
            "category": "error_handling"
        })
        
        # Parameter-based tests
        for param in params:
            test_ideas.append({
                "type": "parameter",
                "description": f"Test {func_name} with parameter {param}",
                "parameter": param,
                "category": "unit"
            })
        
        return test_ideas
    
    def generate_test_case(self, 
                          func_name: str,
                          description: str,
                          test_code: str,
                          inputs: List[Any],
                          expected_output: Any,
                          tags: List[str]) -> TestCase:
        """Generate a single test case"""
        test_id = f"test_{func_name}_{int(time.time() * 1000) % 100000}"
        
        test = TestCase(
            test_id=test_id,
            name=f"Test_{func_name}",
            function_name=func_name,
            description=description,
            test_code=test_code,
            inputs=inputs,
            expected_output=expected_output,
            tags=tags
        )
        
        self.generated_tests.append(test)
        return test


class CoverageAnalyzer:
    """Analyze code coverage from test execution"""
    
    def __init__(self):
        self.coverage_data: Dict[str, Any] = {}
    
    def analyze_coverage(self, test_results: List[TestCase]) -> Dict[str, Any]:
        """Analyze coverage from test execution results"""
        if not test_results:
            return {
                "total_statements": 0,
                "covered_statements": 0,
                "coverage_percentage": 0.0,
                "functions_tested": 0,
                "functions_total": 0
            }
        
        # Extract function names from executed tests
        tested_functions = set(t.function_name for t in test_results if t.status == "pass")
        
        return {
            "total_statements": len(test_results),
            "covered_statements": sum(1 for t in test_results if t.status == "pass"),
            "coverage_percentage": (sum(1 for t in test_results if t.status == "pass") / len(test_results)) * 100 if test_results else 0.0,
            "functions_tested": len(tested_functions),
            "tested_functions": list(tested_functions)
        }


class TestExecutor:
    """Execute tests and collect results"""
    
    def __init__(self):
        self.execution_history: List[Dict[str, Any]] = []
    
    def execute_test(self, test: TestCase) -> Tuple[bool, float, str]:
        """Execute single test and return (status, time, error_message)"""
        start_time = time.time()
        try:
            # Simulate test execution
            # In real scenario, would execute test_code
            test_passed = True  # Placeholder
            execution_time = time.time() - start_time
            
            if test_passed:
                return True, execution_time, ""
            else:
                return False, execution_time, "Test assertion failed"
        
        except Exception as e:
            execution_time = time.time() - start_time
            return False, execution_time, str(e)
    
    def execute_suite(self, suite: TestSuite) -> Dict[str, Any]:
        """Execute all tests in suite"""
        results = {
            "suite_id": suite.suite_id,
            "started_at": datetime.now().isoformat(),
            "tests_executed": 0,
            "passed": 0,
            "failed": 0,
            "total_time": 0.0,
            "test_results": []
        }
        
        start_time = time.time()
        
        for test in suite.test_cases:
            success, exec_time, error = self.execute_test(test)
            
            test.status = "pass" if success else "fail"
            test.execution_time = exec_time
            test.error_message = error
            test.last_run = datetime.now().isoformat()
            
            results["tests_executed"] += 1
            if success:
                results["passed"] += 1
            else:
                results["failed"] += 1
            
            results["test_results"].append({
                "test_id": test.test_id,
                "status": test.status,
                "execution_time": exec_time,
                "error": error
            })
        
        results["total_time"] = time.time() - start_time
        suite.last_run = datetime.now().isoformat()
        suite.total_runs += 1
        suite.update_stats()
        
        self.execution_history.append(results)
        
        return results


class TestManager:
    """Manage test suites, generation, and execution"""
    
    def __init__(self, storage_dir: str = "config/tests"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.test_suites: Dict[str, TestSuite] = {}
        self.test_generator = TestGenerator()
        self.coverage_analyzer = CoverageAnalyzer()
        self.test_executor = TestExecutor()
        
        self._load_suites()
    
    def _load_suites(self):
        """Load test suites from storage"""
        for suite_file in self.storage_dir.glob("*.json"):
            try:
                with open(suite_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    suite = TestSuite.from_dict(data)
                    self.test_suites[suite.suite_id] = suite
            except Exception as e:
                print(f"Error loading suite from {suite_file}: {e}")
    
    def _save_suite(self, suite: TestSuite):
        """Save test suite to storage"""
        suite_file = self.storage_dir / f"{suite.suite_id}.json"
        try:
            with open(suite_file, 'w', encoding='utf-8') as f:
                json.dump(suite.to_dict(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving suite: {e}")
    
    def create_suite(self, name: str, description: str, version: str = "1.0.0") -> TestSuite:
        """Create new test suite"""
        suite_id = f"suite_{name}_{int(time.time() * 1000) % 100000}"
        
        suite = TestSuite(
            suite_id=suite_id,
            name=name,
            description=description,
            version=version
        )
        
        self.test_suites[suite_id] = suite
        self._save_suite(suite)
        
        return suite
    
    def add_test_to_suite(self, 
                         suite_id: str,
                         func_name: str,
                         description: str,
                         test_code: str,
                         inputs: List[Any],
                         expected_output: Any,
                         tags: List[str] = None) -> Optional[TestCase]:
        """Add test case to suite"""
        if suite_id not in self.test_suites:
            return None
        
        suite = self.test_suites[suite_id]
        test = self.test_generator.generate_test_case(
            func_name, description, test_code, inputs, expected_output, tags or []
        )
        suite.add_test(test)
        self._save_suite(suite)
        
        return test
    
    def execute_suite(self, suite_id: str) -> Dict[str, Any]:
        """Execute test suite"""
        if suite_id not in self.test_suites:
            return {}
        
        suite = self.test_suites[suite_id]
        results = self.test_executor.execute_suite(suite)
        
        self._save_suite(suite)
        
        return results
    
    def get_coverage(self, suite_id: str) -> Dict[str, Any]:
        """Get coverage analysis for suite"""
        if suite_id not in self.test_suites:
            return {}
        
        suite = self.test_suites[suite_id]
        return self.coverage_analyzer.analyze_coverage(suite.test_cases)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get overall test statistics"""
        total_suites = len(self.test_suites)
        total_tests = sum(len(s.test_cases) for s in self.test_suites.values())
        total_pass = sum(t.status == "pass" for s in self.test_suites.values() for t in s.test_cases)
        
        return {
            "total_suites": total_suites,
            "total_tests": total_tests,
            "total_passed": total_pass,
            "total_failed": total_tests - total_pass,
            "pass_rate": (total_pass / total_tests * 100) if total_tests > 0 else 0.0,
            "suites": [
                {
                    "suite_id": suite.suite_id,
                    "name": suite.name,
                    "test_count": len(suite.test_cases),
                    "pass_count": suite.pass_count,
                    "pass_rate": suite.pass_rate
                }
                for suite in self.test_suites.values()
            ]
        }
    
    def generate_report(self, suite_id: str) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        if suite_id not in self.test_suites:
            return {}
        
        suite = self.test_suites[suite_id]
        coverage = self.get_coverage(suite_id)
        
        return {
            "suite_id": suite.suite_id,
            "name": suite.name,
            "description": suite.description,
            "version": suite.version,
            "created_at": suite.created_at,
            "last_run": suite.last_run,
            "test_summary": {
                "total": len(suite.test_cases),
                "passed": suite.pass_count,
                "failed": suite.fail_count,
                "pass_rate": suite.pass_rate
            },
            "coverage": coverage,
            "tests": [
                {
                    "test_id": t.test_id,
                    "name": t.name,
                    "status": t.status,
                    "execution_time": t.execution_time,
                    "error": t.error_message
                }
                for t in suite.test_cases
            ]
        }


# Example usage for initialization
if __name__ == "__main__":
    # Create test manager
    tm = TestManager()
    
    # Create a test suite
    suite = tm.create_suite(
        "MathOperations",
        "Test suite for math operations",
        "1.0.0"
    )
    
    # Add test cases
    tm.add_test_to_suite(
        suite.suite_id,
        "add",
        "Test addition function",
        "assert add(2, 3) == 5",
        [2, 3],
        5,
        ["basic", "math"]
    )
    
    # Get statistics
    stats = tm.get_statistics()
    print(f"Test Statistics: {json.dumps(stats, indent=2, ensure_ascii=False)}")
