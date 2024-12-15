import os
import smtplib
from email.message import EmailMessage
from string import Template
from typing import List

import numpy as np
import pandas as pd

credentials = (os.getenv("EMAIL_USERNAME"), os.getenv("EMAIL_PASSWORD"))


def _load_saved_results() -> List[pd.DataFrame]:
    sub_directories = os.listdir("data")
    data = []
    for sub_directory in sub_directories:
        sub_directory = os.path.join("data", sub_directory)
        for file in os.listdir(sub_directory):
            file_path = os.path.join(sub_directory, file)
            if not file_path.endswith(".csv"):
                continue
            df = pd.read_csv(file_path)
            df["File Name"] = file
            df["Email address"] = df["Email address"].str.lower()
            data.append(df)
    return data


def _get_max_score(df: pd.DataFrame):
    def percent(score):
        if not pd.isna(score):
            current_score, max_score = score.split("/")
            current_score = int(current_score)
            max_score = int(max_score)
            return round(current_score / max_score * 100)

    def email_prefix(email_address):
        if not pd.isna(email_address):
            return email_address.split("@")[0].lower()

    df = df.loc[:, ["Score", "Email address", "File Name"]]
    df["Email prefix"] = df["Email address"].apply(email_prefix)
    df["Percent"] = df.loc[:, "Score"].apply(percent)
    df["Quiz Number"] = df["File Name"].str.extract(r'(\d+)').astype(int)
    df = df.groupby(["Quiz Number", "Email prefix"]).max()
    df["Result Comment"] = np.where(df["Percent"] > 75, "Kvíz máš splněný :-)",
                                    "Na tento kvíz se prosím ještě podívej a zkus výsledek trochu vylepšit.")
    df = df.reset_index(drop=False)
    return df


def _send_email(email_to: List[str], results_df: pd.DataFrame, course_name: str, server):
    with open(os.path.join("templates", "email_template.txt"), encoding="utf-8") as f:
        template = f.read()
    results_df = results_df.sort_values("Quiz Number")
    results = [f"Kvíz č. {x["Quiz Number"]}: {x["Percent"]} % ({x["Result Comment"]})" for _, x in
               results_df.iterrows()]
    results = "\n".join(results)
    email = Template(template).substitute({"course_name": course_name, "results": results})
    msg = EmailMessage()
    msg["Subject"] = f"{course_name} - kvízy"
    msg["From"] = os.getenv("EMAIL_USERNAME")
    msg["To"] = email_to
    msg.set_content(email)
    server.send_message(msg)


def process_results(course_name):
    results_df = _load_saved_results()
    max_score_df = [_get_max_score(df) for df in results_df]
    max_score_df = pd.concat(max_score_df)
    email_addresses = pd.concat(results_df)[["Email address"]].dropna()
    server = smtplib.SMTP(os.getenv("SMTP_HOST"), 587)
    server.starttls()
    server.login(os.getenv("EMAIL_USERNAME"), os.getenv("EMAIL_PASSWORD"))
    for email_prefix in max_score_df["Email prefix"].unique():
        email_to = list(set(
            email_addresses[email_addresses["Email address"].str.startswith(email_prefix)]["Email address"].tolist()))
        _send_email(email_to, max_score_df[max_score_df["Email prefix"] == email_prefix], course_name, server)
    server.quit()
