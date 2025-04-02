import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import latex
from pathlib import Path
mpl.rcParams.update(mpl.rcParamsDefault)

fp = Path("C:/Users/jmartin4/OneDrive - NREL/General - FE RCC DFM Project/Task 3/RCC ASPEN Data Final Paper.xlsx")

df = pd.read_excel(fp,sheet_name='WC Plots 3 (2)',header=1,index_col=1)
df = df.iloc[1:29,1:6]
df = df.fillna(0)

barwidth = 0.6
line_width = 2

mpl.rcParams['hatch.linewidth'] = line_width
mpl.rcParams['font.sans-serif']  = 'Arial'
mpl.rcParams['font.size']  = 16
# mpl.rcParams['text.usetex'] = True

plt.figure(figsize=(6,10))
plt.axes((.2,.1,.78,.68))

itemlist = ['Hydrogen Production',
    'Nat. Gas Production',
    'CO$_2$ Capture',
    'Reactor Other',]

colorlist = [[0,    0.8,    0],
             [0.25,    .75,      1],
             [0.5,  0.25,   0],
             [0.5,  0.5,    0.5],]

hatchlist = ['///',
             '\\\\\\',
             '',
             '///',
             '\\\\\\',
             '',
             '',
             '///',
             '\\\\\\',]

# itemlist = np.flipud(itemlist)
# colorlist = np.flipud(colorlist)
# hatchlist = np.flipud(hatchlist)

total = np.zeros(5)

for idx, item in enumerate(itemlist): 
    data = df.loc[item]
    face_color = list(np.multiply(colorlist[idx],int((hatchlist[idx]==''))) + 1*(hatchlist[idx]!=''))
    edge_color = colorlist[idx]
    # if idx<2:
    #     modifier = .5
    #     bottoms = total#+data.values
    # else:
    #     modifier = .5-barwidth
    #     bottoms = total
    # if idx == 2:
    #     itemlabel = 'Hydrogen'
    # elif idx == 3:
    #     itemlabel = 'Natural Gas'
    # else:
    itemlabel = item
    modifier = .5-barwidth/2
    plt.bar(np.arange(0,df.shape[1])+modifier,
            height=data.values,
            bottom=total,
            align='edge',
            width=barwidth,
            hatch=hatchlist[idx],
            edgecolor=edge_color,
            facecolor=face_color,
            linewidth=line_width,
            label=itemlabel)
    total = np.add(total,data.values)
    # if idx == 1:
    #     ratios = df.loc['H2:MeOH Ratio']
    #     for r_idx, ratio in enumerate(ratios):
    #         if r_idx>0:
    #             plt.text(r_idx+modifier+barwidth/2,total[r_idx]-data.values[r_idx]/2,
    #                     'H$_2$:\nMeOH\nRatio=\n{:.3f}'.format(ratio),
    #                     bbox=dict(boxstyle="square",fc='w',ec=None),
    #                     horizontalalignment='center',verticalalignment='center')
for idx, item in enumerate(total):
    t = plt.text(idx+.5,item+.5,"{:.1f}".format(item),ha='center',
                 bbox=dict(boxstyle="square",ec='k',fc='w',))
    xlabel = plt.text(idx+.5,-.2,df.columns.values[idx],fontsize=12,
                      horizontalalignment='center',verticalalignment='top')

# plt.grid('on')
plt.ylim([0,14])
plt.xlabel
plt.tick_params(length=8)
plt.xlim([0,3])
ax = plt.gca()
xtick_labels = [' \n ']*4
ax.set_xticks(np.arange(0,4))
ax.set_yticks(np.arange(0,15,1))
plt.xlabel('Methanol Production Process')
plt.ylabel('Water Consumption (WC)\n(kg-H$_2$O/kg-methanol)')
labels = ax.set_xticklabels(xtick_labels,horizontalalignment='center',fontsize=12)
# for idx, label in enumerate(labels):
#     label_y = label.get_position()[1]
#     label.set_position((idx+.5,label_y))
L = plt.legend(bbox_to_anchor=(1.02, 1.25),ncol=2,edgecolor='k')
L.set_alpha(0)
# plt.show()
plt.savefig('Bar_chart_mpl_wc.png',dpi=300)