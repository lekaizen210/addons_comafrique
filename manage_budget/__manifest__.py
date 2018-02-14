{
    'name':'Manage budget',
    'description':"""
        - Gerer les lignes du budget au niveau des expression de bession
    """,
    'author':'Veone',
    'sequence':3,
    'depends':['base','purchase_requisition_extension'],
    'data':[
        'views/budget.xml',
    ],
}