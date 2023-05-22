from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.contrib.auth.views import LoginView, PasswordResetView, PasswordChangeView
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.views import View
from django.contrib.auth.decorators import login_required
from .forms import RegisterForm, LoginForm, UpdateUserForm, UpdateProfileForm


class RegisterView(View):
    form_class = RegisterForm
    initial = {"key": "value"}
    template_name = "users/register.html"

    def dispatch(self, request, *args, **kwargs):
        # will redirect to the home page if a user tries to access the register page while logged in
        if request.user.is_authenticated:
            return redirect(to="/")

        # else process dispatch as it otherwise normally would
        return super(RegisterView, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = self.form_class(initial=self.initial)
        return render(request, self.template_name, {"form": form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)

        if form.is_valid():
            form.save()

            username = form.cleaned_data.get("username")
            messages.success(request, f"Account created for {username}")

            return redirect(to="login")

        return render(request, self.template_name, {"form": form})


# Class based view that extends from the built in login view to add a remember me functionality
class CustomLoginView(LoginView):
    form_class = LoginForm

    def form_valid(self, form):
        remember_me = form.cleaned_data.get("remember_me")

        if not remember_me:
            # set session expiry to 0 seconds. So it will automatically close the session after the browser is closed.
            self.request.session.set_expiry(0)

            # Set session as modified to force data updates/cookie to be saved.
            self.request.session.modified = True

        # else browser session will be as long as the session cookie time "SESSION_COOKIE_AGE" defined in settings.py
        return super(CustomLoginView, self).form_valid(form)


class ResetPasswordView(SuccessMessageMixin, PasswordResetView):
    template_name = "users/password_reset.html"
    email_template_name = "users/password_reset_email.html"
    subject_template_name = "users/password_reset_subject"
    success_message = (
        "We've emailed you instructions for setting your password, "
        "if an account exists with the email you entered. You should receive them shortly."
        " If you don't receive an email, "
        "please make sure you've entered the address you registered with, and check your spam folder."
    )
    success_url = reverse_lazy("users-home")


class ChangePasswordView(SuccessMessageMixin, PasswordChangeView):
    template_name = "users/change_password.html"
    success_message = "Successfully Changed Your Password"
    success_url = reverse_lazy("users-home")


@login_required
def profile(request):
    if request.method == "POST":
        user_form = UpdateUserForm(request.POST, instance=request.user)
        profile_form = UpdateProfileForm(
            request.POST, request.FILES, instance=request.user.profile
        )

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Your profile is updated successfully")
            return redirect(to="users-profile")
    else:
        user_form = UpdateUserForm(instance=request.user)
        profile_form = UpdateProfileForm(instance=request.user.profile)

    return render(
        request,
        "users/profile.html",
        {"user_form": user_form, "profile_form": profile_form},
    )


from django.shortcuts import render
from django import forms
from django.urls import reverse
from django.http import HttpResponseRedirect
import openpyxl
from django.template import RequestContext
from django.http import HttpResponse
import pandas as pd
import sys
from .forms import FileForm, StatForm
from .models import File
from django.contrib import messages
from django.shortcuts import render, redirect
import requests, random


pd.options.mode.chained_assignment = None  # default='warn'


class NewTaskForm(forms.Form):
    task = forms.CharField(label="New Task Name")
    priority = forms.IntegerField(label="Priority", min_value=1, max_value=4)


def upload_file(request):
    if request.method == "POST":
        form = FileForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            # return redirect('file_list')
    else:
        form = FileForm()
    return render(request, "upload.html", {"form": form})


@login_required
def read(request):
    if request.method == "POST":
        form = FileForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()

            # Get the uploaded file
            excel_fileSTAT = "media/STATEMENT"
            excel_fileEFT = "media/EFT.xls"
            excel_fileDD = "media/DD.xls"
            excel_fileCHQ = "media/KES.xls"

            sdf = pd.read_fwf(
                excel_fileSTAT, header=None, widths=[13, 20, 15, 9, 32, 16], index=False
            )

            sortdf = sdf.sort_values(0)

            val = sortdf.loc[(sortdf[1] == "BALANCE AT PERIOD EN"), 4].iloc[0]

            df = sortdf.loc[sortdf[5].isin(["KES1020000010001"])]
            df.loc[df[4].str.endswith("-"), 4] = "-" + df.loc[
                df[4].str.endswith("-"), 4
            ].str.strip("- ")
            pd.to_numeric([4])

            cleandf = df[[1, 2, 4]]
            cleandf.columns = ["NARRATION", "FT", "AMOUNT"]

            cleandf["AMOUNT"] = cleandf["AMOUNT"].str.replace(",", "").astype(float)

            cleandf = cleandf.sort_values(["AMOUNT"])

            print(cleandf.head(2))

            postivesum = cleandf[cleandf["AMOUNT"] > 0]["AMOUNT"].sum()
            negativesum = cleandf[cleandf["AMOUNT"] < 0]["AMOUNT"].sum()

            DDrawreport = pd.read_excel(excel_fileDD, index_col=False)
            DDrawreport[["PROCNO", "DESTACCOUNT"]] = DDrawreport[
                ["PROCNO", "DESTACCOUNT"]
            ].astype(str)
            DDreport = DDrawreport[
                (
                    DDrawreport["STATUSID"].isin([1])
                    & (
                        ~DDrawreport["DESTBANK"].isin(
                            ["NCBA BANK KENYA PLC", "NIC BANK PLC"]
                        )
                    )
                )
            ]
            DDdf = DDreport[["POLICY1", "FTREFERENCE", "AMOUNT"]]
            DDdf.columns = ["POLICY1", "FT", "AMOUNT"]
            DDdf["AMOUNT"] = DDdf["AMOUNT"].astype(float)

            DDsum = DDdf["AMOUNT"].sum()

            EFTdata = pd.read_excel(excel_fileEFT, index_col=False)
            EFTdata[["PROCNO", "DESTACCOUNT"]] = EFTdata[
                ["PROCNO", "DESTACCOUNT"]
            ].astype(str)
            EFTdf = EFTdata[["ACHBULKID", "TRNREF", "AMOUNT"]]
            EFTdf.columns = ["ACHBULKID", "FT", "AMOUNT"]
            # EFTdf ['AMOUNT'] = EFTdf ['AMOUNT'].astype(float)
            EFTsum = EFTdf["AMOUNT"].sum()

            CHQraw = pd.read_excel(excel_fileCHQ, index_col=False)
            CHQraw[["PROCNO", "DESTACCOUNT", "CHEQUENO"]] = CHQraw[
                ["PROCNO", "DESTACCOUNT", "CHEQUENO"]
            ].astype(str)

            if "STATUSID" in CHQraw:
                print("STATUSID FOUND")
                CHQs = CHQraw[
                    (
                        CHQraw["STATUSID"].isin([1])
                        & (
                            ~CHQraw["DESTBANK"].isin(
                                ["NCBA BANK KENYA PLC", "NIC BANK PLC"]
                            )
                        )
                        & (CHQraw["STAGE"].isin(["ACH CREATION", "COMPLETE"]))
                    )
                ]
            else:
                print("NO EXCLUDED CHEQUES FOUND")
                CHQs = CHQraw[
                    (~CHQraw["DESTBANK"].isin(["NCBA BANK KENYA PLC", "NIC BANK PLC"]))
                    & (CHQraw["STAGE"].isin(["ACH CREATION"]))
                ]

            if CHQs["CBS_REJECT_REASON"].str.contains("NOCREDIT").any():
                print("CREDIT-DUPLICATE VALUES")
                CHQdf = CHQs[["CHEQUENO", "CBS_REJECT_REASON", "AMOUNT"]]
                CHQdf[["FT", "FT1", "FT2"]] = CHQdf.CBS_REJECT_REASON.str.split(
                    "[,-]", expand=True
                )
                CHQclr = CHQdf[["CHEQUENO", "FT1", "AMOUNT"]]
                CHQclr.columns = ["CHEQUENO", "FT", "AMOUNT"]
            else:
                CHQdf = CHQs[["CHEQUENO", "CBS_REJECT_REASON", "AMOUNT"]]
                CHQdf[["FT", "FT1"]] = CHQdf.CBS_REJECT_REASON.str.split(
                    "[,]", expand=True
                )
                CHQclr = CHQdf[["CHEQUENO", "FT1", "AMOUNT"]]
                CHQclr.columns = ["CHEQUENO", "FT", "AMOUNT"]
                print("NO DUPLICATE ENTRIES")

            CHQsum = CHQclr["AMOUNT"].sum()

            print(CHQclr.head(2))

            print("Let Reconciliation Begin")

            frames = [DDdf, EFTdf, CHQclr]

            allcleared = pd.concat(frames)

            left_join = pd.merge(cleandf, allcleared, on="FT", how="left")

            T24E = left_join[(~left_join["AMOUNT_y"].notnull())]

            left_join2 = pd.merge(allcleared, cleandf, on="FT", how="left")

            CPE = left_join2[(~left_join2["AMOUNT_y"].notnull())]

            totaldebits = DDsum + CHQsum
            summarydata = [
                ["TOTAL STATEMENT CREDITS", postivesum],
                ["TOTAL STATEMENT DEBITS", negativesum],
                ["DIRECT DEBITS", DDsum],
                ["CHEQUES", CHQsum],
                ["EFTs", EFTsum],
                ["TOTAL DEBITS CLEARED", totaldebits],
                ["BALANCE AT THE END", val],
            ]
            summarydf = pd.DataFrame(summarydata, columns=["DESCRIPTION", "AMOUNT"])

            reversals = cleandf[cleandf.duplicated(["FT"], keep=False)]
            reversals2 = allcleared[
                (allcleared.duplicated(["FT"], keep=False))
                & (allcleared["FT"].str.contains("FT"))
            ]

            CHQsDf = CHQs.applymap(
                lambda x: x.encode(
                    "unicode_escape"
                ).decode(  # Basically, it escapes the unicode characters if they exist
                    "utf-8"
                )
                if isinstance(x, str)
                else x
            )

            amountcheck = left_join[(left_join["AMOUNT_y"].notnull())]
            amountcheck["Diff"] = amountcheck["AMOUNT_y"] - abs(amountcheck["AMOUNT_x"])

            WorryDiff = amountcheck.loc[(abs(amountcheck.Diff)) > 0.5]

            context = {"summarydata": summarydata}

            output_path = "./Recon.xlsx"
            with pd.ExcelWriter(output_path) as writer:
                cleandf.to_excel(writer, sheet_name="Statement", index=False)
                print("Copied the Statement Entries")
                allcleared.to_excel(writer, sheet_name="Cleared", index=False)
                print("Copied the CP Cleared Entries")
                T24E.to_excel(writer, sheet_name="T24 Exceptions", index=False)
                print("Created T24 Exceptions")
                CPE.to_excel(writer, sheet_name="CP Exceptions", index=False)
                print("Created Chequepoint Exceptions")
                summarydf.to_excel(writer, sheet_name="Summary", index=False)
                print("Created the Summary Sheet")
                DDreport.to_excel(writer, sheet_name="DDS", index=False)
                print("Copied Cleared DDs")
                EFTdata.to_excel(writer, sheet_name="EFTs", index=False)
                print("Copied Cleared EFTs")
                CHQsDf.to_excel(writer, sheet_name="CHQs", index=False)
                print("Copied Cleared CHQs")
                reversals.to_excel(
                    writer, sheet_name="REVERSALS FROM LIVE", index=False
                )
                print("Reversals Detected...")
                WorryDiff.to_excel(writer, sheet_name="AMOUNT_CHECK", index=False)
                reversals2.to_excel(writer, sheet_name="CLEARED DUPLICATE", index=False)

            html = render(request, "users/read.html", context)
            response = HttpResponse(content_type="text/html")
            response.write(html)

            # Add the binary file to the response
            with open("Recon.xlsx", "rb") as f:
                response.content = f.read()
                response["Content-Disposition"] = 'attachment; filename="Recon.xlsx"'

                return response

    else:
        form = FileForm()

    return render(request, "users/read.html", {"form": form, "process_complete": False})


quotes = [
    "The harder I work, the luckier I get. - Samuel Goldwyn",
    "Success is no accident. It is hard work, perseverance, learning, studying, sacrifice, and most of all, love of what you are doing. - Pelé",
    "There are no shortcuts to any place worth going. - Beverly Sills",
    "The future belongs to those who believe in the beauty of their dreams. - Eleanor Roosevelt",
    "The only place where success comes before work is in the dictionary. - Vidal Sassoon",
    "Dreams don't work unless you do. - John C. Maxwell",
    "Success is the sum of small efforts, repeated day in and day out. - Robert Collier",
    "The only limit to our realization of tomorrow will be our doubts of today. - Franklin D. Roosevelt",
    "Don't watch the clock; do what it does. Keep going. - Sam Levenson",
    "Hard work beats talent when talent doesn't work hard. - Tim Notke",
    "Believe you can, and you're halfway there. - Theodore Roosevelt",
    "The harder the conflict, the greater the triumph. - George Washington",
    "Success is not the key to happiness. Happiness is the key to success. If you love what you are doing, you will be successful. - Albert Schweitzer",
    "Success usually comes to those who are too busy to be looking for it. - Henry David Thoreau",
    "The difference between ordinary and extraordinary is that little extra. - Jimmy Johnson",
    "The only way to do great work is to love what you do. - Steve Jobs",
    "The future depends on what you do today. - Mahatma Gandhi",
    "Success is the result of perfection, hard work, learning from failure, loyalty, and persistence. - Colin Powell",
    "Success is not final, failure is not fatal: It is the courage to continue that counts. - Winston Churchill",
    "The secret to success is to know something nobody else knows. - Aristotle Onassis",
]


def home(request):
    quote = random.choice(quotes)
    context = {"quote": quote}
    return render(request, "users/home.html", context)


@login_required
def stat(request):
    if request.method == "POST":
        form = StatForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()

            # Get the uploaded file
            statement = "media/STATEMENT"
            pstatement = "media/PSTATE"

            sdf = pd.read_fwf(
                statement, header=None, widths=[13, 20, 15, 9, 32, 16], index=False
            )
            sortdf = sdf.sort_values(0)
            df = sortdf.loc[sortdf[5].isin(["KES1020000010001"])]
            df.loc[df[4].str.endswith("-"), 4] = "-" + df.loc[
                df[4].str.endswith("-"), 4
            ].str.strip("- ")
            pd.to_numeric([4])

            cleandf = df[[1, 2, 4]]
            cleandf.columns = ["NARRATION", "FT", "AMOUNT"]

            cleandf["AMOUNT"] = cleandf["AMOUNT"].str.replace(",", "").astype(float)

            cleandf = cleandf.sort_values(["AMOUNT"])

            psdf = pd.read_fwf(
                pstatement, header=None, widths=[13, 20, 15, 9, 32, 16], index=False
            )
            sortpdf = psdf.sort_values(0)
            val = sortpdf.loc[(sortpdf[1] == "BALANCE AT PERIOD EN"), 4].iloc[0]
            dfp = sortpdf.loc[sortpdf[5].isin(["KES1020000010001"])]
            dfp.loc[dfp[4].str.endswith("-"), 4] = "-" + dfp.loc[
                dfp[4].str.endswith("-"), 4
            ].str.strip("- ")
            pd.to_numeric([4])

            cleanpdf = dfp[[1, 2, 4]]
            cleanpdf.columns = ["NARRATION", "FT", "AMOUNT"]

            cleanpdf["AMOUNT"] = cleanpdf["AMOUNT"].str.replace(",", "").astype(float)

            cleanpdf = cleanpdf.sort_values(["AMOUNT"])

            postivesumd = cleanpdf[cleanpdf["AMOUNT"] > 0]["AMOUNT"].sum()
            negativesumd = cleanpdf[cleanpdf["AMOUNT"] < 0]["AMOUNT"].sum()

            left_join = pd.merge(cleanpdf, cleandf, on="FT", how="left")

            T24Ep = left_join[(~left_join["AMOUNT_y"].notnull())]

            summarydata = [
                ["TOTAL STATEMENT CREDITS", postivesumd],
                ["TOTAL STATEMENT DEBITS", negativesumd],
                ["BALANCE AT THE END", val],
            ]
            summarypdf = pd.DataFrame(summarydata, columns=["DESCRIPTION", "AMOUNT"])

            output_path_stat = "./Stat.xlsx"

            with pd.ExcelWriter(output_path_stat) as writer:
                T24Ep.to_excel(writer, sheet_name="T24 Exceptions", index=False)
                print("Created T24 Exceptions")
                summarypdf.to_excel(writer, sheet_name="Summary", index=False)
                print("Created the Summary Sheet")

            html = render(request, "users/stat.html")
            response = HttpResponse(content_type="text/html")
            response.write(html)

            # Add the binary file to the response
            with open("Stat.xlsx", "rb") as f:
                response.content = f.read()
                response["Content-Disposition"] = 'attachment; filename="Stat.xlsx"'

                return response

    else:
        form = StatForm()

    return render(request, "users/stat.html", {"form": form, "process_complete": False})


from django.http import JsonResponse


def my_view(request):
    efts = "media/EFT.xls"

    eftdf = pd.read_excel(efts, index_col=False, dtype="str")
    eftdf["CUSTACCOUNT"] = eftdf["CUSTACCOUNT"].map(str)
    eftdf["DESTACCOUNT"] = eftdf["DESTACCOUNT"].map(str)
    clearedefts = eftdf[
        [
            "CUSTACCOUNT",
            "CUSTNAME",
            "DESTBANK",
            "DESTBRANCH",
            "DESTACCOUNT",
            "DESTACCTITLE",
            "TRNREF",
            "AMOUNT",
            "VALUEDATE",
            "REMARKS",
            "ENDTOENDID",
        ]
    ]
    clearedefts.to_excel("./Cleared_EFTs.xlsx", sheet_name="CLEARED EFTS", index=False)

    html = render(request, "users/test.html")
    response = HttpResponse(content_type="text/html")
    response.write(html)

    # Add the binary file to the response
    with open("Cleared_EFTs.xlsx", "rb") as f:
        response.content = f.read()
        response["Content-Disposition"] = 'attachment; filename="Cleared_EFTs.xlsx"'

    return response
