---
title: Attribute Association Nodes
permalink: /aag_intro/aag_nodes
nav_order: 1
parent: Attribute Association Graphs
---

# Attribute Association Nodes in More Detail
{: .no_toc }

Nodes describe information about a single attribute and its distribution across different groups. Here, an *attribute* 
is a de-duplicated triplet of table, variable and value in the dataset. Therefore, multiple entries, e.g. patients, can 
share the same attribute. General information about the attribute and its statistical traits are captured as 
*parameters*.

## Table of contents
{: .no_toc .text-delta } 
- TOC
{:toc}

## Node Parameters
The node parameters of an AAG can be split into general information and statistical parameters.

### General Attribute Information

| Parameter   | Description                                                                                                                                                                                                                                                                                                                                                                               | Datatype                         | Example                                  |
|-------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------|------------------------------------------|
| name        | The variable name                                                                                                                                                                                                                                                                                                                                                                         | string                           | SysBloodPressure                         |
| value       | The unique variable value                                                                                                                                                                                                                                                                                                                                                                 | string, integer or decimal       | high                                     |
| description | A short text describing the meaning of the variable, or adding context such as a unit of measurement. This parameter is optional and can be set during the metadata editing                                                                                                                                                                                                               | string                           | sitting, mmHg                            |
| refRange    | The reference range for "normal" values of a binned metric variable. This parameter only exists, when the variable was binned during translation to a base graph. This reference range was either set manually during metadata editing, or calculated by GraphXplore to include the middle 60% of values. All values above this reference range are considered "high", and below as "low" | list of two integers or decimals | [0,120]                                  |
| groups      | A list of all group names together with their number of members. The order of group names gives the order of statistical metrics which are lists. If the positive and negative group were set during AAG creation, these groups have a "[+]" and "[-]" at the end of their string                                                                                                         | list of strings                  | ["disease (100)[+]", "control (900)[-]"] |

All general attribute information (apart from the "group" parameter) is taken directly from the 
base graph that was generated when translating your relational dataset to a graph form.

### Statistical Attribute Metrics

For the formulas, let $g_1,\dots,g_n$ be the number of group members, and $a_1,\dots,a_n$ be the 
number of group members having a valid (i.e. not a missing) value for this attribute.

| Parameter             | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | Datatype                             | Formula                       | Example    |
|-----------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------|-------------------------------|------------|
| count                 | The number of members of each group having this attribute                                                                                                                                                                                                                                                                                                                                                                                                                     | list of non-negative integers        | $c_i$                         | [80, 445]  |
| missing               | The ratio of members of each group having a missing value (e.g. a contaminated blood sample or invalid measurement) for this attribute's variable. If this ratio is high (e.g. between 0.5 and 1.0), the expressiveness of the other statistical metrics could be limited                                                                                                                                                                                                     | list of decimals between 0.0 and 1.0 | ${1 - \\dfrac{a_i}{g_i}}$     | [0.0, 0.1] |
| prevalence            | The ratio of members of each group having this attribute. Group members with missing values are excluded. High values might indicate that this attribute is frequently observed within the group                                                                                                                                                                                                                                                                              | list of decimals between 0.0 and 1.0 | ${p_i = \\dfrac{c_i}{a_i}}$   | [0.8, 0.5] |
| prevalence_difference | The absolute difference between group prevalence, also know as risk difference. If positive and negative group are set, the prevalence difference between these two groups is calculated. If they are not set, the maximum absolute pairwise prevalence difference is calculated. If only one group exists, this parameter will be empty. A high difference might indicate a potentially high specificity of the attribute for a group                                        | decimal between 0.0 and 1.0          | $\\vert p_i - p_j\\vert$      | 0.3        |
| prevalence_ratio      | The ratio of group prevalence, also known as the risk ratio. If positive and negative group are set, the prevalence ratio is calculated as the larger prevalence divived be the smaller (or equal) prevalence of these two. If they are not set, the overall maximum prevalence is divided by the overall minimum prevalence. If only one group exists, this parameter will be empty. A high ratio might indicate a potentially high sensitivity of the attribute for a group | decimal greater or equal to 1.0      | $\\dfrac{max(p_i)}{min(p_i)}$ | 1.6        | 

## Visual Node Appearance and Labels

The visualization of nodes is used to encode some of its statistical attribute parameters. For 
this, the *color* and *size* of its circle are adjusted. Additionally, the same information is encoded 
in the node labels. The thresholds used below are only the default values and can be adjusted 
during AAG creation.
- The *size* captures the frequency of its attribute which GraphXplore defines as the maximum group 
  prevalence $p$:
    - $p \geq 0.5$: The node is labeled as *highly frequent* and depicted with the largest circle
    - $0.1 \leq p < 0.5$: The node is labeled as *frequent* and depicted with a medium-sized circle
    - $p < 0.1$: The node is labeled as *infrequent* and depicted with the smallest circle
- The *color* captures the distinction of the attribute between the positive and negative group. 
As a result, the coloring is only used when the AAG has defined positive and negative group. 
GraphXplore uses the prevalence difference $d$ and prevalence ratio $r$ for the distinction:
    - $d \geq 0.2$ or $r \geq 2.0$: The node is labeled as *highly related* and colored in red, if 
      the positive group prevalence as larger, or labeled as *highly inverse* and colored in blue, 
      if the negative group prevalence is larger
    - $d < 0.2$ and $r < 2.0$ and ($d \geq 0.1$ or $r \geq 1.5$): The node is labeled as *related* 
      and colored in orange if  the positive group prevalence as larger, or labeled as *inverse* 
      and colored in turquoise, if the negative group prevalence is larger
    - $d < 0.1$ and $r < 1.5$: The node is labeled as *unrelated* and colored in beige