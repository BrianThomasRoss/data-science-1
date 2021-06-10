"""Machine learning functions."""
import logging
from typing import Any, Dict

import pandas as pd
from fastapi import APIRouter
from pydantic import BaseModel, Field

log = logging.getLogger(__name__)
router = APIRouter()

user = pd.read_csv("app/spokane_zipcodes.csv", header="infer")


class Item(BaseModel):
    """Use this data model to parse the request body JSON."""

    zipCode: int = Field(..., example=99205)
    familySize: int = Field(..., example=4)
    monthlyIncome: int = Field(..., example=4000)
    unEmp90: int = Field(..., example=1)
    foodWrkr: int = Field(..., example=1)
    monthlyRent: int = Field(..., example=800)
    minorGuest: int = Field(..., example=1)
    covidFH: int = Field(..., example=1)


@router.post("/predict")
async def determine_eligibility(
        # Use typing to clearly define what your code expects and returns
        zipCode: int,
        cityName: str,
        familySize: int,
        monthlyIncome: float,
        monthlyRent: float,
        unEmp90: bool,
        foodWrkr: bool,
        minorGuest: str,
        covidFH,
) -> Dict[str, Any]:
    """Endpoint for eligibility requirement logic.

    TODO: Params et al.
    """

    edpNum = 1 if covidFH is "true" else 0
    fpNum = 1 if minorGuest is "true" else 0

    if all(map(lambda x: x is "false",
               [minorGuest, unEmp90, foodWrkr, covidFH])):
        return {
            "SNAP_ERA": 0,
            "SNAP_ERAP": 0,
            "VLP_EDP": edpNum,
            "FP": fpNum,
        }

    def get_income_goal(zip_code: Any, family_size: Any) -> int:
        """Returns the income threshold for a household in a specified
        zip code.

        TODO: Type checking logic should be moved outside this function.

        :param zip_code: The postal code
        :type zip_code: Any

        :param family_size: The number of members in the household.
        :type: Any
        """
        zip_code, family_size = int(zip_code), int(family_size)

        try:
            bound = (user[
                (user["zipcode"] == zipCode)
                & (user["family_members"] == familySize)
                ].iloc[0][4]
            ).astype(int)
        # TODO: Narrow the exception clause
        except Exception as ex:
            log.info("get_income_goal failed", exc_info=True)
            bound = -1
        finally:
            return bound

    income_goal = get_income_goal(zipCode, familySize)

    if income_goal == -1:
        return {"SNAP_ERA": 0,
                "SNAP_ERAP": 0,
                "VLP_EDP": edpNum,
                "FP": fpNum
                }
    try:

        # calculate yearly income from user input of monthly income
        user_income = int(monthlyIncome) * 12

        # I know this seems like it can be done a better way
        # we found multiple ways to accomplish this task with
        # more elegant code, but the code didn't translate from
        # a colab notebook to here very well.  Something about
        # the bool values and the way pandas operates in colab
        # versus how it compares in fastAPI.  Not sure exactly
        # what the problem was, but for now this gets our DS API
        # functioning, and thankfully the logic is not very hard to
        # figure out

        # iterate through every zip in Spokane County, on match
        # go to next step in eligibility check
        for z in user["zipcode"]:

            if int(z) == int(zipCode):

                if unEmp90 == "true":

                    if int(user_income) <= income_goal:

                        if covidFH == "true":

                            cityName = cityName.lower()
                            if cityName.startswith("spokane"):

                                if cityName.endswith("valley"):
                                    era = 0
                                    erap = 1
                                    fpNum = 0
                                else:
                                    era = 1
                                    erap = 0

                            else:
                                era = 1
                                erap = 1
                                fpNum = 0

                        else:
                            era = 0
                            erap = 0
                            fpNum = 0
                    else:
                        era = 0
                        erap = 0
                        fpNum = 0

                else:

                    if int(user_income) <= income_goal:

                        if (int(monthlyRent) / int(monthlyIncome)) >= 0.50:

                            if covidFH == "true":
                                cityName = cityName.lower()
                                if cityName.startswith("spokane"):

                                    if cityName.endswith("valley"):
                                        era = 1
                                        erap = 1
                                        fpNum = 0
                                    else:
                                        era = 1
                                        erap = 0

                                else:
                                    erap = 1
                                    era = 1
                                    fpNum = 0

                            else:
                                erap = 0
                                era = 0
                                fpNum = 0

                        else:
                            erap = 1
                            era = 1

                    else:

                        era = 0
                        erap = 0
                        fpNum = 0

        return {"SNAP_ERAP": erap, "SNAP_ERA": era, "VLP_EDP": edpNum, "FP": fpNum}
    except:
        return {"SNAP_ERAP": erap, "SNAP_ERA": era, "VLP_EDP": edpNum, "FP": fpNum}
