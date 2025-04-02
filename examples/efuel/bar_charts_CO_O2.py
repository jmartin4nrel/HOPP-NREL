import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import latex
from pathlib import Path
mpl.rcParams.update(mpl.rcParamsDefault)

fp = Path("C:/Users/jmartin4/OneDrive - NREL/General - FE RCC DFM Project/Task 3/RCC ASPEN Data CO Paper.xlsx")

num_bars = 6

df = pd.read_excel(fp,sheet_name='LCOM Plots (6)',header=1,index_col=1)
df = df.iloc[1:29,1:num_bars+1]
df = df.fillna(0)

barwidth = 0.3
line_width = 2

mpl.rcParams['hatch.linewidth'] = line_width
mpl.rcParams['font.sans-serif']  = 'Arial'
mpl.rcParams['font.size']  = 16
# mpl.rcParams['text.usetex'] = True

plt.figure(figsize=(10,10))
plt.axes((.13,.11,.85,.68))

itemlist = [
    'O2 Credits - 5¢/kg',
    'Steam Credits',
    'Hydrogen',
    'CO$_2$ Capture',
    'Reactor CAPEX',
    'Reactor Fixed OPEX',
    'Reactor Electricity',
    'MeOH Catalyst',
    'RCC Catalyst Base',
    'RCC Catalyst IWI',
    'NG - $4/MMbtu',
    'Reactor Other',]

colorlist = [
             [0.25,    .75,      1],
             [1,    0.5,    0],
             [0,    0.8,    0],
             [0.5,  0.25,   0],
             [0,    0,      1],
             [1,    0.5,    0],
             [0.75, 0.75,   0],
             [0.8, 0.,     0.8],
             [0,    0,      1],
             [1,    0,      0],
             [0.25,    .75,      1],
             [0.5,  0.5,    0.5],]

hatchlist = [
             '',
             '',
             '///',
             '',
             '',
             '///',
             '\\\\\\',
             '',
             '///',
             '',
             '\\\\\\',
             '\\\\\\',]

# itemlist = np.flipud(itemlist)
# colorlist = np.flipud(colorlist)
# hatchlist = np.flipud(hatchlist)

total = np.zeros(num_bars)

for idx, item in enumerate(itemlist): 
    data = df.loc[item]
    face_color = list(np.multiply(colorlist[idx],int((hatchlist[idx]==''))) + 1*(hatchlist[idx]!=''))
    edge_color = colorlist[idx]
    if idx<2:
        modifier = .5
        bottoms = total#+data.values
    else:
        modifier = .5-barwidth
        bottoms = total
    if idx == 0:
        itemlabel = 'Oxygen Credits'
    if idx == 2:
        itemlabel = 'Hydrogen'
    elif idx == 10:
        itemlabel = 'Natural Gas'
        # data.values[3]=.66
    else:
        itemlabel = item
    plt.bar(np.arange(0,df.shape[1])+modifier,
            height=data.values,
            bottom=bottoms,
            align='edge',
            width=barwidth,
            hatch=hatchlist[idx],
            edgecolor=edge_color,
            facecolor=face_color,
            linewidth=line_width,
            label=itemlabel)
    total = np.add(total,data.values)
    if idx == 1:
        ratios = df.loc['H2:methanol ratio']
        # for r_idx, ratio in enumerate(ratios):
        #     if r_idx>=0:
        #         plt.text(r_idx+modifier+barwidth/2,total[r_idx]-data.values[r_idx]/2,
        #                 'H$_2$:\nMeOH\nRatio=\n{:.3f}'.format(ratio),
        #                 bbox=dict(boxstyle="square",fc='w',ec=None),
        #                 horizontalalignment='center',verticalalignment='center')
for idx, item in enumerate(total):
    # if idx == 3:
    #     t = plt.text(idx+.5,item+.05-.2,"${:.2f}".format(3.96),ha='center',
    #                 bbox=dict(boxstyle="square",ec='k',fc='w',))
    # else:
    t = plt.text(idx+.5,item+.05,"${:.2f}".format(item),ha='center',
                bbox=dict(boxstyle="square",ec='k',fc='w',))
    if idx < 3:
        xlabel = plt.text(idx+.5,-.16,df.columns.values[idx],fontsize=12,
                        horizontalalignment='center',verticalalignment='top')
    else:
        xlabel = plt.text(idx+.5,-.16,df.columns.values[idx][:-2],fontsize=12,
                      horizontalalignment='center',verticalalignment='top')

# plt.grid('on')
plt.ylim([-.15,0.55])
plt.xlabel
plt.tick_params(length=8)
plt.xlim([0,num_bars])
ax = plt.gca()
xtick_labels = [' \n ']*(num_bars+1)
ax.set_xticks(np.arange(0,(num_bars+1)))
ax.set_yticks(np.arange(-.15,0.56,.05))
ax.set_xlabel('Methanol Production Process',labelpad=16)
plt.ylabel('Levelized cost of methanol (LCOM)\n($/kg-methanol)')
labels = ax.set_xticklabels(xtick_labels,horizontalalignment='center',fontsize=12)
# for idx, label in enumerate(labels):
#     label_y = label.get_position()[1]
#     label.set_position((idx+.5,label_y))
L = plt.legend(bbox_to_anchor=(1, 1.25),ncol=3,edgecolor='k')
L.set_alpha(0)
# plt.show()
plt.savefig('Bar_chart_mpl_CO_O2.png',dpi=300)