import myosuite 
from myosuite import gym

env = gym.make('myoChallengeRelocateP2', normalize_act=False, reset_type='random')
for ep in range(5):
    print(f'Episode: {ep} of 5')
    state = env.reset()
    # while True:
    for _ in range(1000):
        action = env.action_space.sample()
        # uncomment if you want to render the task
        env.mj_render()
        # next_state, reward, done, info = 
        _ = env.step(action)
        # state = next_state
        # if done: 
        #     break