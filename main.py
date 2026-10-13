from agent import agent


def main():
    result = agent.invoke({})
    print(result["newsletter"])


if __name__ == "__main__":
    main()
