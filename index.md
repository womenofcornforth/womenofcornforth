---
layout: default
title: Home
description: An archive of stories, photographs and memories from the village of Cornforth — known to those who grew up there as Doggie.
---

<section class="hero">
  <h1>{{ site.title }}</h1>
  <p class="tagline">{{ site.tagline }}</p>
  <p class="lede">
    Voices, memories and photographs from the women — and men — who shaped
    life in Cornforth, the County Durham village locals know as <em>Doggie</em>.
  </p>
</section>

<section>
  <h2>Start here</h2>
  <ul class="entry-list">
    {% assign intro = site.tales | where: "slug", "introduction" | first %}
    {% if intro %}
    <li>
      <a href="{{ intro.url | relative_url }}">{{ intro.title }}</a>
      {% if intro.subtitle %}<p class="excerpt">{{ intro.subtitle }}</p>{% endif %}
      {% if intro.excerpt %}<p class="excerpt">{{ intro.excerpt }}</p>{% endif %}
    </li>
    {% endif %}
    <li>
      <a href="{{ '/stories/' | relative_url }}">All the women's stories</a>
      <p class="excerpt">Individual biographies collected from family, friends and neighbours.</p>
    </li>
    <li>
      <a href="{{ '/tales/' | relative_url }}">Doggie's Tales</a>
      <p class="excerpt">Essays on everyday village life: housework, marriage, pennies, smells, Mondays.</p>
    </li>
    <li>
      <a href="{{ '/photos/' | relative_url }}">Photographs</a>
      <p class="excerpt">{{ site.data.photos.size }} photographs from around the village and its families.</p>
    </li>
  </ul>
</section>

<section>
  <h2>Recently added stories</h2>
  <ul class="entry-list">
    {% assign recent = site.stories | sort: "title" | slice: 0, 6 %}
    {% for s in recent %}
    <li>
      <a href="{{ s.url | relative_url }}">{{ s.title }}</a>
      {% if s.excerpt %}<p class="excerpt">{{ s.excerpt }}</p>{% endif %}
    </li>
    {% endfor %}
  </ul>
  <p><a href="{{ '/stories/' | relative_url }}">See all stories →</a></p>
</section>
