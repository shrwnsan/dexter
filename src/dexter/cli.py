from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from dexter.agent import Agent
from dexter.utils.intro import print_intro
from dexter.utils.input_validator import get_safe_user_input
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory

def main():
    print_intro()
    agent = Agent()

    # Create a prompt session
    session = PromptSession(history=InMemoryHistory())

    while True:
        try:
          # Prompt the user for input
          raw_query = session.prompt(">> ")

          # Handle exit commands
          if raw_query.lower() in ["exit", "quit"]:
              print("Goodbye!")
              break

          if raw_query:
              # Validate and sanitize user input
              safe_query, error = get_safe_user_input(raw_query)

              if error:
                  print(f"❌ Input validation failed: {error}")
                  print("Please enter a valid financial research query.")
                  continue

              # Run the agent with validated input
              agent.run(safe_query)

        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break


if __name__ == "__main__":
    main()
