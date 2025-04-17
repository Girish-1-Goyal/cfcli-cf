import click
import colorama
from colorama import Fore, Style
from pathlib import Path
from datetime import datetime
from ..api.session import CFSession
from ..api.contest import ContestAPI
from ..api.problem import ProblemAPI
from ..api.submission import SubmissionAPI

# Initialize colorama
colorama.init()

# Initialize global session and APIs
cf_session = CFSession()
contest_api = ContestAPI(cf_session)
problem_api = ProblemAPI(cf_session)
submission_api = SubmissionAPI(cf_session)

@click.group()
def cli():
    """Codeforces CLI - Automate your CP workflow"""
    pass

@cli.command()
@click.option('--handle', prompt='Your Codeforces handle', help='Your Codeforces handle', 
              default=lambda: os.getenv("CF_HANDLE", ""))
@click.option('--key', prompt='Your Codeforces API key', help='Your Codeforces API key',
              default=lambda: os.getenv("CF_API_KEY", ""))
@click.option('--secret', prompt='Your Codeforces API secret', help='Your Codeforces API secret',
              default=lambda: os.getenv("CF_API_SECRET", ""))
def login(handle, key, secret):
    """Validate Codeforces credentials"""
    # Set credentials in session
    cf_session.handle = handle
    cf_session.api_key = key
    cf_session.api_secret = secret
    
    # Validate credentials with a test API call
    try:
        response = cf_session.call_api("user.info", {"handles": handle})
        if response and response.get("status") == "OK":
            print(f"{Fore.GREEN}Authentication successful! Welcome, {handle}!{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.RED}Authentication failed. Please check your credentials.{Style.RESET_ALL}")
            return False
    except Exception as e:
        print(f"{Fore.RED}Error during authentication: {e}{Style.RESET_ALL}")
        return False

@cli.command()
@click.argument('type', type=click.Choice(['upcoming', 'running', 'past']), default='upcoming')
@click.option('--limit', default=5, help='Number of contests to show')
def fetch(type, limit):
    """Fetch contest information"""
    if not cf_session.is_authenticated():
        print(f"{Fore.YELLOW}Not authenticated. Using public API access.{Style.RESET_ALL}")
    
    try:
        response = contest_api.get_contests(type, limit)
        if response.get("status") != "OK":
            print(f"{Fore.RED}Error fetching contests: {response.get('comment', 'Unknown error')}{Style.RESET_ALL}")
            return
            
        contests = response.get("result", [])
        
        # Display contests
        if not contests:
            print(f"{Fore.YELLOW}No {type} contests found.{Style.RESET_ALL}")
            return
        
        print(f"\n{Fore.CYAN}== {type.capitalize()} Contests =={Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'ID':<8} {'Name':<50} {'Start Time':<25} {'Duration'}{Style.RESET_ALL}")
        print("-" * 90)
        
        for contest in contests:
            start_time = datetime.fromtimestamp(contest.get('startTimeSeconds', 0))
            duration_mins = contest.get('durationSeconds', 0) // 60
            duration_str = f"{duration_mins // 60}h {duration_mins % 60}m"
            
            print(f"{contest.get('id', 'N/A'):<8} {contest.get('name', 'Unknown')[:47]+'...' if len(contest.get('name', '')) > 50 else contest.get('name', 'Unknown'):<50} {start_time.strftime('%Y-%m-%d %H:%M:%S'):<25} {duration_str}")
        
    except Exception as e:
        print(f"{Fore.RED}Error fetching contests: {e}{Style.RESET_ALL}")

@cli.command()
@click.argument('contest_id')
@click.argument('problem_index', required=False)
@click.option('--template-dir', default=None, help='Directory containing C++ templates')
@click.option('--all', is_flag=True, help='Generate files for all problems in the contest')
def generate(contest_id, problem_index, template_dir, all):
    """Generate C++ source files for contest problems"""
    # Validate contest ID
    try:
        contest_id = int(contest_id)
    except ValueError:
        print(f"{Fore.RED}Contest ID must be a number.{Style.RESET_ALL}")
        return

    if all:
        # Fetch contest problems
        try:
            response = contest_api.get_contest_problems(contest_id)
            if response.get("status") != "OK":
                print(f"{Fore.RED}Failed to fetch contest problems: {response.get('comment', 'Unknown error')}{Style.RESET_ALL}")
                return
                
            problems = response.get("result", [])
            
            if not problems:
                print(f"{Fore.YELLOW}No problems found for contest {contest_id}.{Style.RESET_ALL}")
                return
                
            print(f"{Fore.CYAN}Generating files for {len(problems)} problems in contest {contest_id}...{Style.RESET_ALL}")
            
            for problem in problems:
                problem_index = problem.get("index")
                if not problem_index:
                    continue
                    
                result = problem_api.generate_problem_file(contest_id, problem_index, template_dir)
                if result.get("status") == "OK":
                    print(f"{Fore.GREEN}Created {result['result']['filename']} successfully!{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}Problem URL: {result['result']['url']}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}Error generating file: {result.get('comment', 'Unknown error')}{Style.RESET_ALL}")
                    
        except Exception as e:
            print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")
            
    else:
        # Single problem generation
        if not problem_index:
            print(f"{Fore.RED}Problem index is required when not using --all flag.{Style.RESET_ALL}")
            return
            
        problem_index = problem_index.upper()
        if not re.match(r'^[A-Z][0-9]?$', problem_index):
            print(f"{Fore.RED}Problem index must be a letter optionally followed by a number (e.g., A, B, C1).{Style.RESET_ALL}")
            return

        result = problem_api.generate_problem_file(contest_id, problem_index, template_dir)
        if result.get("status") == "OK":
            print(f"{Fore.GREEN}Created {result['result']['filename']} successfully!{Style.RESET_ALL}")
            print(f"{Fore.CYAN}Problem URL: {result['result']['url']}{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}Error generating file: {result.get('comment', 'Unknown error')}{Style.RESET_ALL}")

@cli.command()
@click.argument('filename')
def submit(filename):
    """Submit a solution to Codeforces"""
    file_path = Path(filename)
    
    # Check if file exists
    if not file_path.exists():
        print(f"{Fore.RED}File {filename} not found.{Style.RESET_ALL}")
        return
    
    # Extract contest ID and problem index from filename
    match = re.match(r'Contest(\d+)_([A-Z][0-9]?)\.cpp', file_path.name)
    if not match:
        print(f"{Fore.YELLOW}Filename doesn't follow the expected pattern 'Contest{contest_id}_{problem_index}.cpp'.{Style.RESET_ALL}")
        contest_id = click.prompt("Enter contest ID", type=int)
        problem_index = click.prompt("Enter problem index (e.g., A, B, C1)", type=str).upper()
    else:
        contest_id = int(match.group(1))
        problem_index = match.group(2)
    
    # Read source code
    try:
        with open(file_path, 'r') as f:
            source_code = f.read()
    except Exception as e:
        print(f"{Fore.RED}Error reading file: {e}{Style.RESET_ALL}")
        return
    
    # Submit solution
    result = submission_api.submit_solution(contest_id, problem_index, source_code)
    if result.get("status") == "OK":
        submission_id = result["result"]["submission_id"]
        print(f"{Fore.GREEN}Solution submitted successfully!{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Submission ID: {submission_id}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Run 'cfcli status {submission_id}' to check the verdict.{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}Submission failed: {result.get('comment', 'Unknown error')}{Style.RESET_ALL}")

@cli.command()
@click.argument('submission_id', required=False)
@click.option('--contest-id', type=int, help='Contest ID to check status for all submissions')
def status(submission_id, contest_id):
    """Check submission status"""
    if not submission_id and not contest_id:
        print(f"{Fore.RED}Please provide either a submission ID or a contest ID.{Style.RESET_ALL}")
        return
    
    try:
        if submission_id:
            # Check status for a specific submission
            result = submission_api.get_submission_status(submission_id)
            
            if result.get("status") == "IN_QUEUE":
                print(f"{Fore.YELLOW}Submission is in queue...{Style.RESET_ALL}")
                return
                
            if result.get("status") != "OK":
                print(f"{Fore.RED}Error checking status: {result.get('comment', 'Unknown error')}{Style.RESET_ALL}")
                return
                
            data = result["result"]
            verdict = data.get("verdict")
            
            # Color based on verdict
            color = Fore.GREEN if verdict == "OK" else Fore.RED
            time_consumed = data.get("timeConsumedMillis", "N/A")
            memory_consumed = data.get("memoryConsumedBytes", "N/A") // 1024  # Convert to KB
            
            print(f"{color}Verdict: {verdict}{Style.RESET_ALL}")
            print(f"Time: {time_consumed} ms")
            print(f"Memory: {memory_consumed} KB")
            
            if "testset" in data and "testCount" in data:
                passed = data.get("passedTestCount", 0)
                total = data.get("testCount", 0)
                print(f"Tests: {passed}/{total}")
        
        else:
            # Check all submissions for a contest
            response = contest_api.get_contest_status(contest_id)
            if response.get("status") != "OK":
                print(f"{Fore.RED}Error fetching submissions: {response.get('comment', 'Unknown error')}{Style.RESET_ALL}")
                return
                
            submissions = response.get("result", [])
            
            if not submissions:
                print(f"{Fore.YELLOW}No submissions found for contest {contest_id}.{Style.RESET_ALL}")
                return
            
            print(f"\n{Fore.CYAN}== Submissions for Contest {contest_id} =={Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'ID':<12} {'Problem':<10} {'Verdict':<15}{Style.RESET_ALL}")
            print("-" * 40)
            
            for submission in submissions:
                subm_id = submission.get("id")
                problem_index = submission.get("problem", {}).get("index")
                verdict = submission.get("verdict", "IN QUEUE")
                
                color = Fore.GREEN if verdict == "OK" else Fore.RED if verdict not in ["IN QUEUE", "TESTING"] else Fore.YELLOW
                print(f"{subm_id:<12} {problem_index:<10} {color}{verdict}{Style.RESET_ALL}")
            
    except Exception as e:
        print(f"{Fore.RED}Error checking status: {e}{Style.RESET_ALL}")

if __name__ == "__main__":
    cli() 