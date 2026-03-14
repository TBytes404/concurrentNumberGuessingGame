import random
class ComputerGame:
    def __init__(self, difficulty):
        self.LOWER_BOUND = 0
        self.UPPER_BOUND = 100*difficulty
        self.DIFFICULTY = difficulty
        self.MAX_GUESSES = 9
        self.guesses = 0
        self.CPU_NUM = random.randint(self.LOWER_BOUND,self.UPPER_BOUND)

    def is_in_range(self, guess):
        return guess >= self.LOWER_BOUND and guess <= self.UPPER_BOUND

    def get_guess(self):
        guess = -1
        while not self.is_in_range(guess):
            guess_input = input(
                f"Guess a number between {self.LOWER_BOUND} and {self.UPPER_BOUND} ({self.MAX_GUESSES-self.guesses} guesses remaining):"
            )
            if not guess_input.isnumeric():
                print("Enter a valid number")
                continue
            guess = int(guess_input)
            if not self.is_in_range(guess):
                print(f"Your number must be between {self.LOWER_BOUND} and {self.UPPER_BOUND}")
        return guess

    '''
    return values:
    "lower" -> the argument is HIGHER than the number to guess
    "higher" -> the argument is LOWER than the number to guess
    "correct" -> the argument is equal to the correct number
    '''
    def get_guess_feedback(self, guess):
        if guess == self.CPU_NUM:
            return "correct"
        elif guess < self.CPU_NUM:
            return "higher"
        elif guess > self.CPU_NUM:
            return "lower"

    def run_game(self):
        print("Welcome to the game!")
        print("Try to guess the secret number!")
        while True:
            if self.guesses >= self.MAX_GUESSES:
                print("You have run out of guesses, better luck next time")
                return

            guess = self.get_guess()
            self.guesses += 1
            feedback = self.get_guess_feedback(guess)
            if feedback == "correct":
                print("Correct!")
                print(f"You have guessed the number {self.CPU_NUM} in {self.guesses} guesses")
                return
            elif feedback == "higher":
                print(f"The secret number is higher than {guess}")
            elif feedback == "lower":
                print(f"The secret number is lower than {guess}")
