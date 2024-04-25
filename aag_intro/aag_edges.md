---
title: Attribute Association Edges
permalink: /aag_intro/aag_edges
nav_order: 2
parent: Attribute Association Graphs
---

# Attribute Association Edges in More Detail
{: .no_toc }

The edges of an AAG capture conditional relationships between attributes. For the rest of this 
section lets consider the conditional relationship of an attribute $$y$$ to the 
presence of an attribute $$x$$. The corresponding edge in the AAG would point from the node for 
attribute $$x$$ to the node for attribute $$y$$.

## Table of contents
{: .no_toc .text-delta } 
- TOC
{:toc}

## Edge Parameters

For the formulas, let $$c_{x_1},\dots,c_{x_n}$$ be the count of attribute $$x$$ in the different 
groups, and $$p_{y_1},\dots,p_{y_n}$$ be the prevalence of $$y$$ in the different groups.

| Parameter              | Description                                                                                                                                                                                                                                                                                                            | Datatype                              | Formula                                | Example                                        |
|------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------|----------------------------------------|------------------------------------------------|
| groups                 | A list of all group names together with their number of members, same as the node parameter "groups". The order of group names gives the order of statistical metrics which are lists. If the positive and negative group were set during AAG creation, these groups have a "[+]" and "[-]" at the end of their string | list of strings                       |                                        | ["disease (100)[+]", "control (900)[-]"]       |
| co_occurrence          | The number of members of each group have both attributes $$x$$ and $$y$$                                                                                                                                                                                                                                               | list of integers                      | $$o_i$$                                | [50, 600]                                      |
| conditional_prevalence | The ratio of members of each group with the presence of attribute $$x$$ that also have attribute $$y$$. This is the empirical version of the conditional probability $$P(y \vert x)$$                                                                                                                                  | list of decimals between 0.0 and 1.0  | $$\tilde{p_i} = \dfrac{o_i}{c_{x_i}}$$ | [0.625, 0.75]                                  |
| conditional_increase   | The difference between the conditional prevalence of $$y$$ given $$x$$ and the (unconditional) prevalence of $$y$$ for each group. If the conditional prevalence is smaller than the unconditional one, this value will be negative showing a conditional decrease                                                     | list if decimals between -1.0 and 1.0 | $${\tilde{p_i} - p_{y_i}}$$            | [0.125, -0.15]                                 |
| increase_ratio         | The ratio of the conditional prevalence of $$y$$ given $$x$$ and the (unconditional) prevalence of $$y$$ for each group. If this ratio is smaller than 1.0 it marks a conditional decrease                                                                                                                             | list of positive decimals             | $$\dfrac{\tilde{p_i}}{p_{y_i}}$$       | [1.25, 0.833]                                  |

## Visual Edge Appearance

Edges are depicted as arrows. The *thickness* of edges is used to depict the strength of the 
conditional relationship. The same information is encoded in the edge type. Additionally, 
attributes which share an edge tend to be visualized close together. As a result, groups of 
attributes which have some level of conditional relationship with each other tend to cluster in the 
visualization. GraphXplore measures the strength of a conditional relationship by its largest 
conditional increase $$i$$ and the largest conditional increase ratio $$r_i$$ across groups. The 
thresholds used below are only the default values and can be adjusted during AAG creation.
- $$i \geq 0.2$$ or $$r_i \geq 2.0$$: The edge type *high relation* is assigned and the arrow is 
  depicted with the greatest thickness
- $$i < 0.2$$ and $$r_i < 2.0$$ and ($$i \geq 0.1$$ or $$r_i \geq 1.5$$): The edge type *medium relation* 
  is assigned and the arrow is depicted with a medium thickness
- $$i < 0.1$$ and $$r_i < 1.5$$: The edge type *low relation* is assigned and the arrow is depicted 
  with the smallest thickness