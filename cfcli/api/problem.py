from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime
from .session import CFSession

class ProblemAPI:
    def __init__(self, session: CFSession):
        self.session = session
        self.template_dir = Path.home() / ".cfcli" / "templates"
        self.template_dir.mkdir(parents=True, exist_ok=True)

    def get_problem(self, contest_id: int, problem_index: str) -> Dict:
        """Fetch problem details"""
        try:
            response = self.session.call_api("contest.standings", {
                "contestId": contest_id,
                "from": 1,
                "count": 1
            })
            
            if response.get("status") != "OK":
                return {"status": "FAILED", "comment": response.get("comment", "Unknown error")}
                
            problems = response.get("result", {}).get("problems", [])
            problem = next((p for p in problems if p.get("index") == problem_index), None)
            
            if not problem:
                return {"status": "FAILED", "comment": f"Problem {problem_index} not found in contest {contest_id}"}
                
            return {"status": "OK", "result": problem}
            
        except Exception as e:
            return {"status": "FAILED", "comment": str(e)}

    def generate_problem_file(self, contest_id: int, problem_index: str, template_dir: Optional[Path] = None) -> Dict:
        """Generate a source file for a problem"""
        try:
            # Get problem details
            problem_response = self.get_problem(contest_id, problem_index)
            if problem_response.get("status") != "OK":
                return problem_response
                
            problem = problem_response["result"]
            
            # Determine template directory
            if template_dir is None:
                template_dir = self.template_dir
                
            template_file = template_dir / "template.cpp"
            
            # Create default template if it doesn't exist
            if not template_file.exists():
                with open(template_file, 'w') as f:
                    f.write("""#include <iostream>
#include <vector>
#include <algorithm>
#include <string>
#include <map>
#include <set>

using namespace std;

void solve() {
    // Your solution here
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t = 1;
    // cin >> t;
    while (t--) {
        solve();
    }
    
    return 0;
}
""")

            # Create output file
            output_filename = f"Contest{contest_id}_{problem_index}.cpp"
            output_path = Path(output_filename)
            
            # Generate problem URL
            problem_url = f"https://codeforces.com/contest/{contest_id}/problem/{problem_index}"
            
            # Read template
            with open(template_file, 'r') as src:
                template_content = src.read()
            
            # Add header with problem URL
            header = f"""/**
 * Problem: Codeforces {contest_id}{problem_index}
 * URL: {problem_url}
 * Date: {datetime.now().strftime('%Y-%m-%d')}
 */
"""
            # Write to output file
            with open(output_filename, 'w') as dest:
                dest.write(header + "\n" + template_content)
            
            return {"status": "OK", "result": {
                "filename": output_filename,
                "url": problem_url
            }}
            
        except Exception as e:
            return {"status": "FAILED", "comment": str(e)} 