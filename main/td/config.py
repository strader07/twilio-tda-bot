import pandas as pd

df = pd.read_csv("config/config.csv")

USERNAME = df[df["fields"]=="USERNAME"].iloc[0]["values"]
PASSWORD = df[df["fields"]=="PASSWORD"].iloc[0]["values"]
ACCOUNT_NUMBER = str(df[df["fields"]=="ACCOUNT_NUMBER"].iloc[0]["values"])
REDIRECT_URI = df[df["fields"]=="REDIRECT_URI"].iloc[0]["values"]

CLIENT_ID = df[df["fields"]=="CLIENT_ID"].iloc[0]["values"]

question1 = df[df["fields"]=="question1"].iloc[0]["values"]
question2 = df[df["fields"]=="question2"].iloc[0]["values"]
question3 = df[df["fields"]=="question3"].iloc[0]["values"]
question4 = df[df["fields"]=="question4"].iloc[0]["values"]

myanswer1 = df[df["fields"]=="myanswer1"].iloc[0]["values"]
myanswer2 = df[df["fields"]=="myanswer2"].iloc[0]["values"]
myanswer3 = df[df["fields"]=="myanswer3"].iloc[0]["values"]
myanswer4 = df[df["fields"]=="myanswer4"].iloc[0]["values"]

twilio_sid = "ACd158e4f056a19875e54b1d64806dacfa"
twilio_auth = "3251b7fc5c834cd8d25aa26d8a4c7489"
twilio_number = "+16789213470"

broadcast_numbers = "+14028198102,+14045529199"
