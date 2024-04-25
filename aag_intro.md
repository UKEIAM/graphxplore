---
title: Attribute Association Graphs
permalink: /aag_intro
nav_order: 3
has_children: true
---

# Introduction to Attribute Association Graphs
{: .no_toc }

Here, we explain this novel type of data exploration. Some concepts might be quite different from other statistical 
tools you worked with. Feel free to come back to this tutorial any time during your workflow.

## Table of contents
{: .no_toc .text-delta } 
- TOC
{:toc}

## Use case

Attribute association graphs (AAG) are meant to support you during your data exploration with visual 
highlights of various forms. Note that AAGs capture very basic statistical parameters that are 
intuitive and applicable to any dataset. While this form of data exploration is very accessible 
and can help you to familiarize yourself with your dataset or formulate hypothesis, it does not 
replace thorough statistical inference which should be the next step in your data analysis.

## What is a graph?

A graph in general consists of *nodes* which can represent arbitrary objects and *edges* (also 
called *relationships*) which point from a source node to a target node and describe some 
association between the objects represented by the source and target node. A good example could be 
a set of research articles which are represented as nodes, and edges pointing from one article to 
another article that is cited in the first one. In the visualization of a graph, nodes are 
depicted as spheres (or points) and edges as arrows pointing from the source node sphere to the 
target node sphere. This form of visualization allows to encode different traits of the nodes and 
edges via colors, size of spheres, thickness of arrows, and visual clustering.

## Data Groups

During the generation of an AAG one or multiple groups of primary keys are defined. This could for 
example be disease and control cohorts as they are used in case-control studies, patients with 
different procedures during their hospital stay, or simply all primary keys. GraphXplore 
measures several statistical traits within these groups and their difference (if multiple groups 
were defined). Optionally, some groups can be defined as *positive* or *negative* which will affect 
the parameters and visualization of nodes. This will be explained in later paragraphs.

## AAG Overview

Each node of an AAG represents a so-called *attribute* being a unique variable value. Since 
attributes are unique, two primary keys (e.g. two patients) can share the same attribute (e.g. a 
diagnosis or age group). Nodes describe several statistical metrics about the occurrence of its 
attribute within the selected groups and the difference between group occurrences. In the 
visualization, the attributes are represented as the node's spheres and its statistical parameters 
are encoded via size and color.  

The edges of an AAG capture conditional relationships between attributes. Conditional relationships 
describe how the presence of one attribute influences the presence of another attribute. Does the 
likelihood increase? How does this increase (or decrease) differ between groups? E.g. how does 
reduced renal function affect hemoglobin levels? How does this dependency differ between patients 
with and without hypertension? Compared to nodes capturing information about a single attribute, 
edges might be a little harder to comprehend since the added condition also adds another layer 
of complexity. Feel free to revisit this introduction multiple times until you feel familiar with 
its concepts. Edges are visualized as arrows where the arrow thickness encodes the strength of the 
conditional relationship. Additionally, attributes which are either connected directly by an edge, 
or share a common connected attribute, tend to cluster in the visualization. As a result, groups of 
attributes which have some level of conditional relationship can be explored in the same area of 
the graph visualization.

## How to explore AAGs?

Here, We will talk about how to *interpret* the AAG visualization and how it can help you during 
your data exploration. If you want to know you to operate Neo4J, check out 
[here]({{ site.baseurl }}{% link aag_intro/bloom_navigation.md %}). 
You can learn more about [nodes]({{ site.baseurl }}{% link aag_intro/aag_nodes.md %}) and 
[edges]({{ site.baseurl }}{% link aag_intro/aag_edges.md %}) in detail in their respective subpages.

<figure>
  <img src="../how_to_images/aag_overview.png" alt="drawing">
  <figcaption style="font-style: italic;">AAG birdseye view</figcaption>
</figure>

Above you can see a birdseye view of an AAG in Neo4J Bloom as a screenshot. You can see that there 
are a lot of red and orange nodes in the center with a lot of connections between them. These 
represent attributes statistically related to the positive group (e.g. disease cohort). As they are 
clustered together, they might have some conditional dependencies. On the outer parts of the 
screenshot you can see blue and turquoise nodes in at least two clusters which are statistically 
related to the negative group (e.g. control cohort). Lastly, there are beige nodes throughout the 
screenshot which have roughly similar statistical properties in the positive and negative group and 
thus could be of less interest in the initial exploration. It might be a good idea to start with a 
cluster of nodes with a dark color (red or blue) and zoom in.

<figure>
  <img src="../how_to_images/aag_detailed.png" alt="drawing">
  <figcaption style="font-style: italic;">AAG detailed view</figcaption>
</figure>

Above you can see an example how a few nodes and their edges might look like, e.g. once you zoomed 
in from the birdseye view. The variable name of the attribute is shown in bold in the circle of the 
nodes followed by the value. The size of the nodes indicates how frequently this attribute occurs. 
The beige and red nodes occur very 
frequently, the turquoise and blue nodes frequently, and the orange node infrequently. You might 
want to check out the red node first, as its attribute occurs frequently and is statistically 
related to the positive group. Additionally, it is connected by edges to the orange and beige node.   
The red and orange node share two edges (conditional dependency in both directions), however one of 
these marks a "high impact relation", the other a "medium impact relation". This could be 
interesting to explore. You can double-click on the nodes and edges to inspect them in more detail. 
Regarding the blue node, it might be interesting to find out why it has no edge (i.e. no measured 
conditional dependency) although it is statistically related to the negative group. To summarize,
you might want to explore visual clusters, strongly colored nodes, absence of edges, and of course 
the statistical parameter which are explained in detail in the subpages for 
[nodes]({{ site.baseurl }}{% link aag_intro/aag_nodes.md %}) 
and [edges]({{ site.baseurl }}{% link aag_intro/aag_edges.md %}).