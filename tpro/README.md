### zvert.py
A batch generation of human parcable CSVs from tpro .bin files. 

```
usage: zvert.py [-h] [-CHA] proj set tran radar tpro

positional arguments:
  proj        project if wildcard operators are desired enclose argument in
              double quotes
  set         set if wildcard operators are desired enclose argument in double
              quotes
  tran        transect if wildcard operators are desired enclose argument in
              double quotes
  radar       radar processor (pik1, foc1, foc2)
  tpro        tpro product to analyze [thk, bed, srf, echo,spec,rad_pos], all
              does all except rad_pos

optional arguments:
  -h, --help  show this help message and exit
  -CHA        flag to use CHA root
```

### list_project.py
Lists all the PSTs for a given project and all the sets the were used. Looks in both $WAIS and $CHA and generates separate lists for each. The code looks at what pik1 files exists.

```
usage: list_project.py [-h] [-xped] proj

positional arguments:
  proj        project to list

optional arguments:
  -h, --help  show this help message and exit
  -xped       print xped of each pst
```
