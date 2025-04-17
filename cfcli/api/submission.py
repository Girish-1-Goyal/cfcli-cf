from typing import Dict, List, Optional
import re
from pathlib import Path
from urllib.parse import urljoin
from .session import CFSession

class SubmissionAPI:
    def __init__(self, session: CFSession):
        self.session = session

    def submit_solution(self, contest_id: int, problem_index: str, source_code: str) -> Dict:
        """Submit a solution to Codeforces"""
        try:
            # Ensure we're logged in to the website
            if not self.session.logged_in:
                if not self.session.web_login():
                    return {"status": "FAILED", "comment": "Failed to log in to Codeforces website"}
            
            # Prepare submission
            submit_url = urljoin(self.session.CF_BASE_URL, f"contest/{contest_id}/submit")
            
            # Get CSRF token if needed
            if not self.session.csrf_token:
                response = self.session.session.get(submit_url)
                csrf_pattern = r'name="X-Csrf-Token" content="([^"]+)"'
                match = re.search(csrf_pattern, response.text)
                if not match:
                    return {"status": "FAILED", "comment": "Could not extract CSRF token"}
                self.session.csrf_token = match.group(1)
            
            # Prepare form data
            submit_data = {
                "csrf_token": self.session.csrf_token,
                "action": "submitSolutionFormSubmitted",
                "submittedProblemIndex": problem_index,
                "programTypeId": "54",  # ID for C++17
                "source": source_code,
                "tabSize": "4",
                "sourceFile": ""
            }
            
            # Submit solution
            response = self.session.session.post(submit_url, data=submit_data)
            
            if "You have submitted exactly the same code" in response.text:
                return {"status": "FAILED", "comment": "You have submitted exactly the same code before"}
            
            # Check if submission was successful
            if f"contest/{contest_id}/my" in response.url:
                # Extract submission ID
                match = re.search(r'submissionId="(\d+)"', response.text)
                if match:
                    submission_id = match.group(1)
                    return {"status": "OK", "result": {"submission_id": submission_id}}
                else:
                    return {"status": "FAILED", "comment": "Could not extract submission ID"}
            else:
                return {"status": "FAILED", "comment": "Submission failed"}
                
        except Exception as e:
            return {"status": "FAILED", "comment": str(e)}

    def get_submission_status(self, submission_id: str) -> Dict:
        """Get submission status"""
        try:
            url = urljoin(self.session.CF_BASE_URL, "data/submitSource")
            params = {"submissionId": submission_id}
            
            response = self.session.session.get(url, params=params)
            if response.status_code != 200:
                return {"status": "FAILED", "comment": f"HTTP Error: {response.status_code}"}
            
            data = response.json()
            verdict = data.get("verdict")
            
            if verdict in ["TESTING", ""]:
                return {"status": "IN_QUEUE", "result": data}
            
            return {"status": "OK", "result": data}
            
        except Exception as e:
            return {"status": "FAILED", "comment": str(e)} 