# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna

from typing import Optional, Dict, List

import pandas as pd

from Finish.services import StudentMarkService, TaMarkingService
from Papers.models import Specification


class GraphingDataService:
    """Service for getting data to graph."""

    def __init__(self):
        sms = StudentMarkService()
        tms = TaMarkingService()
        self.spec = Specification.load().spec_dict

        student_dict = sms.get_all_students_download(
            version_info=True, timing_info=False, warning_info=False
        )
        student_keys = sms.get_csv_header(
            self.spec, version_info=True, timing_info=False, warning_info=False
        )
        self.student_df = pd.DataFrame(student_dict, columns=student_keys)

        ta_dict = tms.build_csv_data()
        ta_keys = tms.get_csv_header()

        self.ta_df = pd.DataFrame(ta_dict, columns=ta_keys)

    def get_ta_data(self) -> pd.DataFrame:
        """Return the dataframe of TA data."""
        return self.ta_df

    def get_student_data(self) -> pd.DataFrame:
        """Return the dataframe of student data."""
        return self.student_df

    def get_total_average_mark(self) -> float:
        """Return the average total mark for all students as a float."""
        return self.student_df["total_mark"].mean()

    def get_total_median_mark(self) -> float:
        """Return the median total mark for all students as a float."""
        return self.student_df["total_mark"].median()

    def get_total_stdev_mark(self) -> float:
        """Return the standard deviation of the total marks for all students as a float."""
        return self.student_df["total_mark"].std()

    def get_total_marks(self) -> List[int]:
        """Return the total marks for all students as a list."""
        return self.student_df["total_mark"].tolist()

    def get_average_on_question_as_percentage(self, question_number: int) -> float:
        """Return the average mark on a specific question as a percentage."""
        return (
            100
            * self.student_df[f"q{question_number}_mark"].mean()
            / self.spec["question"][str(question_number)]["mark"]
        )

    def get_averages_on_all_questions_as_percentage(self) -> List[float]:
        """Return the average mark on each question as a percentage."""
        averages = []
        for q in self.spec["question"].keys():
            q = int(q)
            averages.append(self.get_average_on_question_as_percentage(q))
        return averages

    def get_marks_for_all_questions(self, student_df: pd.DataFrame) -> pd.DataFrame:
        """Get the marks for each question as a dataframe.

        Args:
            student_df: The dataframe containing the student data. Should be
                a copy or filtered version of self.student_df.

        Returns:
            A dataframe containing the marks for each question.
        """
        return student_df.filter(regex="q[0-9]*_mark")

    def get_question_correlation_heatmap_data(
        self, student_df: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """Get the correlation heatmap data for the questions.

        Args:
            student_df: Optional dataframe containing the student data. Should be
                a copy or filtered version of self.student_df. If omitted,
                self.student_df is used.

        Returns:
            A dataframe containing the correlation heatmap.
        """
        if student_df is None:
            student_df = self.student_df
        assert isinstance(student_df, pd.DataFrame)

        marks_corr = (
            student_df.filter(regex="q[0-9]*_mark").corr(numeric_only=True).round(2)
        )

        for i, name in enumerate(marks_corr.columns):
            marks_corr.rename({name: "Q" + str(i + 1)}, axis=1, inplace=True)
            marks_corr.rename({name: "Q" + str(i + 1)}, axis=0, inplace=True)

        return marks_corr

    def get_ta_data_for_ta(self, ta_name: str, ta_df: pd.DataFrame) -> pd.DataFrame:
        """Get the dataframe of TA marking data for a specific TA.

        Args:
            ta_name: The TA to get the data for.
            ta_df: The dataframe containing the TA data. Should be a copy or
                filtered version of self.ta_df.

        Returns:
            A dataframe containing the TA data for the specified TA.
        """
        marks = ta_df[ta_df["user"] == ta_name]
        return marks

    def get_all_ta_data_by_ta(self) -> Dict[str, pd.DataFrame]:
        """Get TA marking data for all TAs.

        Returns:
            A dictionary keyed by the TA name, containing the marking
            data for each TA.
        """
        marks_by_ta = {}
        for ta_name in self.ta_df["user"].unique():
            marks_by_ta[ta_name] = self.get_ta_data_for_ta(ta_name, self.ta_df)
        return marks_by_ta

    def get_ta_data_for_question(
        self, question_number: int, ta_df: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """Get the dataframe of TA marking data for a specific question.

        Args:
            question_number: The question to get the data for.
            ta_df: Optional dataframe containing the TA data. Should be a copy or
                filtered version of self.ta_df. If omitted, self.ta_df is used.

        Returns:
            A dataframe containing the TA data for the specified question.
        """
        if ta_df is None:
            ta_df = self.ta_df
        assert isinstance(ta_df, pd.DataFrame)

        question_df = ta_df[ta_df["question_number"] == question_number]
        return question_df

    def get_all_ta_data_by_question(self) -> Dict[int, pd.DataFrame]:
        """Get TA marking data for all questions as a dict.

        Returns:
            A dictionary keyed by the question number, containing the
            marking data for each question.
        """
        marks_by_question = {}
        for question_num in self.ta_df["question_number"].unique():
            marks_by_question[question_num] = self.get_ta_data_for_question(
                question_num, self.ta_df
            )
        return marks_by_question

    def get_times_for_all_questions(self) -> Dict[int, pd.Series]:
        """Get the marking times for all questions.

        Returns:
            A dictionary keyed by the question numbers, containing the
            marking times for each question.
        """
        times_by_question = {}
        for q in self.ta_df["question_number"].unique():
            times_by_question[q] = self.get_ta_data_for_question(q, self.ta_df)[
                "seconds_spent_marking"
            ]
        return times_by_question

    def get_questions_marked_by_this_ta(
        self, ta_name: str, ta_df: pd.DataFrame
    ) -> List[int]:
        """Get the questions that were marked by a specific TA.

        Args:
            ta_name: The TA to get the data for.
            ta_df: The dataframe containing the TA data. Should be a copy or
                filtered version of self.ta_df.

        Returns:
            A list of questions marked by the specified TA.
        """
        return ta_df[ta_df["user"] == ta_name]["question_number"].unique().tolist()

    def get_tas_that_marked_this_question(
        self, question_number: int, ta_df: pd.DataFrame
    ) -> List[str]:
        """Get the TAs that marked a specific question.

        Args:
            question_number: The question to get the data for.
            ta_df: The dataframe containing the TA data. Should be a copy or
                filtered version of self.ta_df.

        Returns:
            A list of TA names that marked the specified question.
        """
        return (
            ta_df[ta_df["question_number"] == question_number]["user"].unique().tolist()
        )

    def get_scores_for_question(
        self, question_number: int, ta_df: Optional[pd.DataFrame] = None
    ) -> List[int]:
        """Get the marks assigned for a specific question.

        Args:
            question_number: The question to get the data for.
            ta_df: Optional dataframe containing the TA data. Should be a copy or
                filtered version of self.ta_df. If omitted, self.ta_df is used.

        Returns:
            A list of marks assigned for the specified question.
        """
        if ta_df is None:
            ta_df = self.ta_df
        assert isinstance(ta_df, pd.DataFrame)

        return ta_df[ta_df["question_number"] == question_number][
            "score_given"
        ].tolist()

    def get_scores_for_ta(
        self, ta_name: str, ta_df: Optional[pd.DataFrame] = None
    ) -> List[int]:
        """Get the marks assigned for by a specific TA.

        Args:
            ta_name: The TA to get the data for.
            ta_df: Optional dataframe containing the TA data. Should be a copy or
                filtered version of self.ta_df. If omitted, self.ta_df is used.

        Returns:
            A list of marks assigned by the specified TA.
        """
        if ta_df is None:
            ta_df = self.ta_df
        assert isinstance(ta_df, pd.DataFrame)

        return ta_df[ta_df["user"] == ta_name]["score_given"].tolist()
