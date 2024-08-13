# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Julian Lapenna
# Copyright (C) 2023-2024 Colin B. Macdonald
# Copyright (C) 2024 Bryan Tanady
# Copyright (C) 2024 Elisa Pan
# Copyright (C) 2024 Andrew Rechnitzer

from __future__ import annotations

import base64
from io import BytesIO

import matplotlib
import matplotlib.patches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from . import DataExtractionService, StudentMarkService
from Papers.services import SpecificationService
from QuestionTags.services import QuestionTagService

RANGE_BIN_OFFSET = 2
HIGHLIGHT_COLOR = "orange"


class MatplotlibService:
    """Service for generating matplotlib plots from data."""

    matplotlib.use("Agg")

    def __init__(self):
        self.des = DataExtractionService()

        self.student_df = self.des._get_student_data()
        self.ta_df = self.des._get_ta_data()
        self.formats = ["base64", "bytes"]

    def ensure_all_figures_closed(self) -> None:
        """Ensure that all matplotlib figures are closed.

        Raises:
            AssertionError: If not all figures are closed.
        """
        assert plt.get_fignums() == [], "Not all matplotlib figures were closed."

    def get_graph_as_BytesIO(self, fig: matplotlib.figure.Figure) -> BytesIO:
        """Return the graph as a BytesIO.

        Args:
            fig: The figure to save.

        Returns:
            The BytesIO object.
        """
        png_bytes = BytesIO()
        fig.savefig(png_bytes, format="png")
        png_bytes.seek(0)
        plt.close(fig)  # Ensure the figure is closed after saving

        return png_bytes

    def get_graph_as_base64(self, bytes: BytesIO) -> str:
        """Return the graph as a base64 encoded string.

        Args:
            bytes: The bytes to encode.

        Returns:
            The base64 encoded string.
        """
        return base64.b64encode(bytes.read()).decode()

    def histogram_of_total_marks(
        self, *, highlighted_sid: str | None = None, format: str = "base64"
    ) -> BytesIO | str:
        """Generate a histogram of the total marks.

        Keyword Args:
            format: The format to return the graph in. Should be either "base64"
                or "bytes". If omitted, defaults to "base64".
            highlighted_sid: The identifier of the student whose standing
                will be highlighted in the chart.

        Returns:
            Base64 encoded string or bytes containing the histogram.
        """
        assert format in self.formats
        self.ensure_all_figures_closed()

        fig, ax = plt.subplots()

        paper_total_marks = SpecificationService.get_total_marks()

        ax.hist(
            self.des.get_totals(),
            bins=np.arange(paper_total_marks + RANGE_BIN_OFFSET) - 0.5,
            ec="black",
            alpha=0.5,
            width=0.8,
            align="mid",
            density=True,
        )
        # Overlay the student's score by highlighting the bar
        if highlighted_sid:
            df = self.des.get_student_data()
            student = df[df["StudentID"] == highlighted_sid]
            student_score = student["Total"].values[0]

            ax = plt.gca()
            for bar in ax.patches:
                assert isinstance(bar, matplotlib.patches.Rectangle)
                bar_left = bar.get_x()
                bar_right = bar_left + bar.get_width()
                if bar_left <= student_score <= bar_right:
                    bar.set_color(HIGHLIGHT_COLOR)
                    bar.set_edgecolor("black")
                    bar.set_linewidth(1.5)
        ax.set_title("Histogram of total marks")
        ax.set_xlabel("Total mark")
        ax.set_ylabel("Proportion of students")
        plt.grid(True, alpha=0.5)

        graph_bytes = self.get_graph_as_BytesIO(fig)
        self.ensure_all_figures_closed()

        if format == "bytes":
            return graph_bytes
        else:
            return self.get_graph_as_base64(graph_bytes)

    def histogram_of_grades_on_question_version(
        self,
        question_idx: int,
        *,
        versions: bool = False,
        student_df: pd.DataFrame | None = None,
        highlighted_sid: str | None = None,
        format: str = "base64",
    ) -> BytesIO | str:
        """Generate a histogram of the grades on a specific question.

        Args:
            question_idx: The question index number, one-based.

        Keyword Args:
            versions: Whether to split the histogram into versions. If omitted,
                defaults to False.
            student_df: Optional dataframe containing the student data. Should be
                a copy or filtered version of self.student_df. If omitted, defaults
                to None and self.student_df is used.
            highlighted_sid: Optional student ID, to show the student's standing
                on the chart.
            format: The format to return the graph in. Should be either "base64"
                or "bytes". If omitted, defaults to "base64".

        Returns:
            Base64 encoded string or bytes containing the histogram.
        """
        if student_df is None:
            student_df = self.student_df

        assert isinstance(student_df, pd.DataFrame)
        assert format in self.formats
        self.ensure_all_figures_closed()

        qlabel = SpecificationService.get_question_label(question_idx)
        ver_column = "q" + str(question_idx) + "_version"
        mark_column = "q" + str(question_idx) + "_mark"
        plot_series = []
        if versions:
            if pd.isna(student_df[ver_column].max()):
                maxver = 0
            else:
                maxver = round(student_df[ver_column].max())
            for version in range(1, maxver + 1):
                plot_series.append(
                    student_df[(student_df[ver_column] == version)][mark_column]
                )
        else:
            plot_series.append(student_df[mark_column])
        fig, ax = plt.subplots(figsize=(6.8, 4.2), tight_layout=True)

        maxmark = SpecificationService.get_question_mark(question_idx)
        bins = np.arange(maxmark + RANGE_BIN_OFFSET) - 0.5

        ax.hist(plot_series, bins=bins, ec="black", alpha=0.5, density=True)
        ax.set_title(f"Histogram of {qlabel} marks")
        ax.set_xlabel(f"{qlabel} mark")
        ax.set_ylabel("Proportion of students")
        if highlighted_sid:
            # Overlay the student's score by highlighting the bar
            df = self.des.get_student_data()
            student_score = df[df["StudentID"] == highlighted_sid][mark_column].values[
                0
            ]
            ax = plt.gca()
            for bar in ax.patches:
                assert isinstance(bar, matplotlib.patches.Rectangle)
                bar_left = bar.get_x()
                bar_right = bar_left + bar.get_width()
                if bar_left <= student_score <= bar_right:
                    bar.set_color(HIGHLIGHT_COLOR)
                    bar.set_edgecolor("black")
                    bar.set_linewidth(1.5)
        if versions:
            labels = [f"Version {i}" for i in range(1, len(plot_series) + 1)]
            ax.legend(
                labels,
                loc="center left",
                bbox_to_anchor=(1, 0.5),
                ncol=1,
                fancybox=True,
            )
        plt.grid(True, alpha=0.5)

        graph_bytes = self.get_graph_as_BytesIO(fig)
        self.ensure_all_figures_closed()

        if format == "bytes":
            return graph_bytes
        else:
            return self.get_graph_as_base64(graph_bytes)

    def boxplot_of_grades_on_question_version(
        self,
        question_idx: int,
        *,
        student_df: pd.DataFrame | None = None,
        highlighted_sid: str | None = None,
        format: str = "base64",
    ) -> BytesIO | str:
        """Generate a boxplot of the grades on a specific question.

        Args:
            question_idx: The question index number, one-based.

        Keyword Args:
            student_df: Optional dataframe containing the student data. Should be
                a copy or filtered version of self.student_df. If omitted, defaults
                to None and self.student_df is used.
            highlighted_sid: Optional student ID, to show the student's standing
                on the chart.
            format: The format to return the graph in. Should be either "base64"
                or "bytes". If omitted, defaults to "base64".

        Returns:
            Base64 encoded string or bytes containing the histogram.
        """
        if student_df is None:
            student_df = self.student_df

        assert isinstance(student_df, pd.DataFrame)
        assert format in self.formats
        self.ensure_all_figures_closed()

        maxmark = SpecificationService.get_question_mark(question_idx)
        qlabel = SpecificationService.get_question_label(question_idx)
        mark_column = "q" + str(question_idx) + "_mark"
        plot_series = [student_df[mark_column]]
        fig, ax = plt.subplots(figsize=(6.8, 2.0), tight_layout=True)

        maxmark = SpecificationService.get_question_mark(question_idx)

        if highlighted_sid:
            # Overlay the student's score by highlighting the bar
            df = self.des.get_student_data()
            student_score = df[df["StudentID"] == highlighted_sid][mark_column].values[
                0
            ]
            ax.plot(student_score, 1, marker="o", markersize=16, color=HIGHLIGHT_COLOR)

        ax.boxplot(
            plot_series,
            widths=0.60,
            capwidths=0.60,
            vert=False,
            showmeans=True,
            meanline=True,
            medianprops={"linewidth": 4, "color": "blue"},
            meanprops={"linewidth": 4, "linestyle": ":", "color": "teal"},
            capprops={"linewidth": 2, "color": "red"},
        )
        # ax.set_title(f"boxplot of {qlabel} marks")
        ax.set_xlabel(f"{qlabel} mark")
        ax.set_yticks([])
        ax.set_xlim(left=-0.5, right=maxmark + 0.5)
        for side in ["top", "right", "left"]:
            ax.spines[side].set_visible(False)

        graph_bytes = self.get_graph_as_BytesIO(fig)
        self.ensure_all_figures_closed()

        if format == "bytes":
            return graph_bytes
        else:
            return self.get_graph_as_base64(graph_bytes)

    def correlation_heatmap_of_questions(
        self, *, corr_df: pd.DataFrame | None = None, format: str = "base64"
    ) -> BytesIO | str:
        """Generate a correlation heatmap of the questions.

        Keyword Args:
            corr_df: Optional dataframe containing the student data. Should be
                a copy or filtered version of self.student_df. If omitted, defaults
                to None and self.student_df is used.
            format: The format to return the graph in. Should be either "base64"
                or "bytes". If omitted, defaults to "base64".

        Returns:
            Base64 encoded string or bytes containing the correlation heatmap.
        """
        if corr_df is None:
            corr_df = self.des._get_question_correlation_heatmap_data()

        assert isinstance(corr_df, pd.DataFrame)
        assert format in self.formats
        self.ensure_all_figures_closed()

        plt.figure(figsize=(7.5, 9))
        sns.heatmap(
            corr_df,
            annot=True,
            cmap="coolwarm",
            vmin=-1,
            vmax=1,
            square=True,
            linewidths=0.5,
            linecolor="black",
            clip_on=False,
            cbar_kws=dict(
                use_gridspec=False,
                location="bottom",
                orientation="horizontal",
                shrink=0.9,
            ),
        )
        plt.title("Correlation between questions")
        plt.xlabel("Question")
        plt.ylabel("Question")

        graph_bytes = self.get_graph_as_BytesIO(plt.gcf())
        self.ensure_all_figures_closed()

        if format == "bytes":
            return graph_bytes
        else:
            return self.get_graph_as_base64(graph_bytes)

    def histogram_of_grades_on_question_by_ta(
        self,
        question_idx: int,
        ta_name: str,
        *,
        ta_df: pd.DataFrame | None = None,
        versions: bool = False,
        format: str = "base64",
    ) -> BytesIO | str:
        """Generate a histogram of the grades on a specific question by a specific TA.

        Args:
            question_idx: The question index to generate the histogram for.
            ta_name: The name of the TA to generate the histogram for.

        Keyword Args:
            ta_df: Optional dataframe containing the ta data. Should be
                a copy or filtered version of self.ta_df. If omitted, defaults
                to None and self.ta_df is used.
            versions: Whether to split the histogram into versions. If omitted,
                defaults to False.
            format: The format to return the graph in. Should be either "base64"
                or "bytes". If omitted, defaults to "base64".

        Returns:
            Base64 encoded string or bytes containing the histogram.
        """
        qlabel = SpecificationService.get_question_label(question_idx)
        if ta_df is None:
            ta_df = self.des._get_ta_data_for_ta(
                ta_name,
                ta_df=self.des._get_ta_data_for_question(question_index=question_idx),
            )

        assert isinstance(ta_df, pd.DataFrame)
        assert format in self.formats
        self.ensure_all_figures_closed()

        fig, ax = plt.subplots(figsize=(6.8, 4.2), tight_layout=True)
        bins = np.arange(ta_df["max_score"].max() + RANGE_BIN_OFFSET) - 0.5

        plot_series = []
        if versions:
            for version in range(1, round(ta_df["question_version"].max()) + 1):
                plot_series.append(
                    ta_df[(ta_df["question_version"] == version)]["score_given"]
                )
        else:
            plot_series.append(ta_df["score_given"])

        ax.hist(
            plot_series,
            bins=bins,
            ec="black",
            alpha=0.5,
        )
        ax.set_title(f"Grades for {qlabel} (by {ta_name})")
        ax.set_xlabel("Mark given")
        ax.set_ylabel("# of times assigned")
        if versions:
            labels = [f"Version {i}" for i in range(1, len(plot_series) + 1)]
            ax.legend(
                labels,
                loc="center left",
                bbox_to_anchor=(1, 0.5),
                ncol=1,
                fancybox=True,
            )

        plt.grid(True, alpha=0.5)

        graph_bytes = self.get_graph_as_BytesIO(fig)
        self.ensure_all_figures_closed()

        if format == "bytes":
            return graph_bytes
        else:
            return self.get_graph_as_base64(graph_bytes)

    def histogram_of_time_spent_marking_each_question(
        self,
        question_idx: int,
        *,
        marking_times_df: pd.DataFrame | None = None,
        versions: bool = False,
        max_time: int = 0,
        bin_width: int = 15,
        format: str = "base64",
    ) -> BytesIO | str:
        """Generate a histogram of the time spent marking a question.

        Args:
            question_idx: The question index to generate the histogram for.

        Keyword Args:
            marking_times_df: Optional dataframe containing the marking data. Should be
                a copy or filtered version of self.ta_df. If omitted, defaults
                to None and self.ta_df is used.
            versions: Whether to split the histogram into versions. If omitted,
                defaults to False.
            max_time: The maximum time to show on the histogram. If omitted,
                defaults to the maximum time in the "seconds_spent_marking" column
                of marking_times_df.
            bin_width: The width of each bin on the histogram. Should be given in
                units of seconds. If omitted, defaults to 15 seconds per bin.
            format: The format to return the graph in. Should be either "base64"
                or "bytes". If omitted, defaults to "base64".

        Returns:
            Base64 encoded string or bytes containing the histogram.
        """
        qlabel = SpecificationService.get_question_label(question_idx)
        if marking_times_df is None:
            marking_times_df = self.ta_df

        assert isinstance(marking_times_df, pd.DataFrame)

        if max_time == 0:
            max_time = round(max(marking_times_df["seconds_spent_marking"].div(60)))

        assert max_time > 0
        assert format in self.formats
        self.ensure_all_figures_closed()

        fig, ax = plt.subplots(figsize=(6.8, 4.2), tight_layout=True)
        bins = (np.arange(0, max_time + bin_width, bin_width) - (bin_width / 2)) / 60.0

        plot_series = []
        if versions:
            for version in range(
                1, round(marking_times_df["question_version"].max()) + 1
            ):
                plot_series.append(
                    marking_times_df[
                        (marking_times_df["question_number"] == question_idx)
                    ][(marking_times_df["question_version"] == version)][
                        "seconds_spent_marking"
                    ].div(
                        60
                    )
                )
        else:
            plot_series.append(
                marking_times_df[(marking_times_df["question_number"] == question_idx)][
                    "seconds_spent_marking"
                ].div(60)
            )

        ax.hist(
            plot_series,
            bins=bins,
            ec="black",
            alpha=0.5,
        )
        ax.set_title(f"Time spent marking {qlabel}")
        ax.set_xlabel("Time spent (min)")
        ax.set_ylabel("# of papers")
        if versions:
            labels = [f"Version {i}" for i in range(1, len(plot_series) + 1)]
            ax.legend(
                labels,
                loc="center left",
                bbox_to_anchor=(1, 0.5),
                ncol=1,
                fancybox=True,
            )
        plt.grid(True, alpha=0.5)

        graph_bytes = self.get_graph_as_BytesIO(fig)
        self.ensure_all_figures_closed()

        if format == "bytes":
            return graph_bytes
        else:
            return self.get_graph_as_base64(graph_bytes)

    def scatter_time_spent_vs_mark_given(
        self,
        question_idx: int,
        times_spent_minutes: list[float] | list[list[float]],
        marks_given: list[float] | list[list[float]],
        *,
        versions: bool = False,
        format: str = "base64",
    ) -> BytesIO | str:
        """Generate a scatter plot of the time spent marking a question vs the mark given.

        Args:
            question_idx: The question index to generate the scatter plot for.
            times_spent_minutes: Listlike containing the marking times in minutes or
                a list of listlikes containing the marking times in minutes for each
                version.
            marks_given: Listlike containing the marks given or a list of listlikes
                containing the marks given for each version.

        Keyword Args:
            versions: Whether to split the scatter plot into versions. If omitted,
                defaults to False.
            format: The format to return the graph in. Should be either "base64"
                or "bytes". If omitted, defaults to "base64".

        Returns:
            Base64 encoded string or bytes containing the scatter plot.
        """
        qlabel = SpecificationService.get_question_label(question_idx)
        assert format in self.formats
        self.ensure_all_figures_closed()

        fig, ax = plt.subplots(figsize=(6.8, 4.2), tight_layout=True)

        if versions is True:
            for i in range(len(times_spent_minutes)):
                ax.scatter(
                    marks_given[i],
                    times_spent_minutes[i],
                    ec="black",
                    alpha=0.5,
                    label="Version " + str(i + 1),
                )
        else:
            ax.scatter(
                marks_given,
                times_spent_minutes,
                ec="black",
                alpha=0.5,
                label="All versions",
            )

        ax.set_title(f"{qlabel}: Time spent vs Mark given")
        ax.set_ylabel("Time spent (min)")
        ax.set_xlabel("Mark given")
        if versions is True:
            ax.legend(loc="center left", bbox_to_anchor=(1, 0.5), ncol=1, fancybox=True)

        plt.grid(True, alpha=0.5)
        maxmark = SpecificationService.get_question_mark(question_idx)
        plt.xlim(left=-0.5, right=maxmark + 0.5)
        plt.ylim(bottom=-0.2)

        graph_bytes = self.get_graph_as_BytesIO(fig)
        self.ensure_all_figures_closed()

        if format == "bytes":
            return graph_bytes
        else:
            return self.get_graph_as_base64(graph_bytes)

    def boxplot_of_marks_given_by_ta(
        self,
        marks: list[list[float]],
        marker_names: list[str],
        question_idx: int,
        *,
        format: str = "base64",
    ) -> BytesIO | str:
        """Generate a boxplot of the marks given by each TA for the specified question.

        The length and order of marks and marker_names should be the same such
        that marks[i] is the list of marks given by marker_names[i].

        Args:
            marks: The dataframe of marks to plot.
            marker_names: The names of the markers.
            question_idx: The question index to plot the boxplot for.

        Keyword Args:
            format: The format to return the graph in. Should be either "base64"
                or "bytes". If omitted, defaults to "base64".

        Returns:
            Base64 encoded string or bytes containing the boxplot.
        """
        qlabel = SpecificationService.get_question_label(question_idx)
        assert len(marks) == len(marker_names)
        assert format in self.formats
        self.ensure_all_figures_closed()

        fig, ax = plt.subplots(figsize=(6.8, 4.2), tight_layout=True)

        # Create a DataFrame to use with Seaborn
        data = pd.DataFrame(marks).T
        data.columns = pd.Index(marker_names)

        sns.boxplot(
            data=data,
            ax=ax,
            orient="h",
        )

        # Set y-ticks and y-tick labels
        ax.set_yticks(range(len(marker_names)))
        ax.set_yticklabels(marker_names)

        ax.set_title(f"{qlabel} boxplot by marker")
        ax.set_xlabel(f"{qlabel} mark")
        ax.tick_params(
            axis="y",
            which="both",  # both major and minor ticks are affected
            left=False,  # ticks along the bottom edge are off
            right=False,  # ticks along the top edge are off
            labelleft=True,
        )

        plt.xlim(
            [
                0,
                self.des._get_ta_data_for_question(question_index=question_idx)[
                    "max_score"
                ].max(),
            ]
        )

        sns.despine()
        graph_bytes = self.get_graph_as_BytesIO(fig)
        self.ensure_all_figures_closed()

        if format == "bytes":
            return graph_bytes
        else:
            return self.get_graph_as_base64(graph_bytes)

    def line_graph_of_avg_marks_by_question(
        self, *, versions: bool = False, format: str = "base64"
    ) -> BytesIO | str:
        """Generate a line graph of the average percentage marks by question.

        Keyword Args:
            versions: Whether to split the line graph into versions. If omitted,
                defaults to False.
            format: The format to return the graph in. Should be either "base64"
                or "bytes". If omitted, defaults to "base64".

        Returns:
            Base64 encoded string or bytes containing the line graph.
        """
        assert format in self.formats
        self.ensure_all_figures_closed()

        plt.figure(figsize=(6.8, 4.2), tight_layout=True)

        question_indices = SpecificationService.get_question_indices()
        if versions is True:
            averages = self.des.get_averages_on_all_questions_versions_as_percentage(
                overall=True
            )
            for i, v in enumerate(averages):
                if i == 0:
                    sns.lineplot(
                        x=question_indices,
                        y=v,
                        marker="o",
                        label="Overall",
                    )
                else:
                    sns.lineplot(
                        x=question_indices,
                        y=v,
                        marker="x",
                        label="Version " + str(i),
                    )
        else:
            sns.lineplot(
                x=question_indices,
                y=self.des.get_averages_on_all_questions_as_percentage(),
                marker="o",
                label="All versions",
            )
        if versions is True:
            plt.legend(
                loc="center left",
                bbox_to_anchor=(1, 0.5),
                ncol=1,
                fancybox=True,
            )
        sns.despine()
        plt.ylim([0, 100])
        plt.title("Average percentage by question")
        # plt.xlabel("Question")
        plt.ylabel("Average mark (%)")
        plt.xticks(
            question_indices,
            labels=SpecificationService.get_question_labels(),
        )

        graph_bytes = self.get_graph_as_BytesIO(plt.gcf())
        self.ensure_all_figures_closed()

        if format == "bytes":
            return graph_bytes
        else:
            return self.get_graph_as_base64(graph_bytes)

    def lollypop_of_pedagogy_tags(
        self, paper_number: int, student_id: str, *, format: str = "base64"
    ) -> BytesIO | str:
        assert format in self.formats
        self.ensure_all_figures_closed()

        student_scores = StudentMarkService().get_marks_from_paper(paper_number)[
            paper_number
        ]
        tag_to_question = QuestionTagService.get_tag_to_question_links()
        n_tags = len(tag_to_question)
        tag_names = sorted(list(tag_to_question.keys()))
        pedagogy_values = []
        # for each tag, compute % student got on each question
        # combine those to get a 'pedagogy value'
        for name in tag_names:
            values = [
                student_scores[qi]["student_mark"] / student_scores[qi]["out_of"]
                for qi in tag_to_question[name]
            ]
            pedagogy_values.append(sum(values) / len(values))

        plt.figure(figsize=(6.8, n_tags * 0.3 + 0.6), tight_layout=True)
        plt.margins(y=0.3)

        df = pd.DataFrame({"tag": tag_names, "values": pedagogy_values})
        ordered_df = df.sort_values(by="tag")
        my_range = range(1, len(df.index) + 1)
        plt.hlines(y=my_range, xmin=0, xmax=df["values"], linewidth=8)
        plt.plot(ordered_df["values"], my_range, "o", markersize=16)
        # note mypy gets grumpy with many matplotlib functions, so
        # convert the pandas series to a list to keep it happy
        plt.yticks(my_range, ordered_df["tag"].to_list())
        plt.xlim(0, 1)

        graph_bytes = self.get_graph_as_BytesIO(plt.gcf())
        self.ensure_all_figures_closed()

        if format == "bytes":
            return graph_bytes
        else:
            return self.get_graph_as_base64(graph_bytes)
