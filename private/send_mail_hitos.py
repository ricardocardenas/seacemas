#import time
import datetime
#from gluon.tools import prettydate
from seaceperu import SEACE

T.force('es')

User = db.auth_user
Process = db.seace_process
Event = db.seace_event
Interest = db.seace_interest

for u in db(User).select(User.ALL):
    print "send_mail_hitos(): user", u.email
    today = datetime.date.today()
    range_begin = today - datetime.timedelta(3)
    range_end = today + datetime.timedelta(15)
    query = (
        (Interest.person == u.id) &
        (Interest.process == Process.id) &
        (Interest.interest_level.belongs((SEACE.INTEREST_OPPORTUNITY, SEACE.INTEREST_HOT))) &
        (Event.proceso == Process.id) &
        (Event.fecha >= range_begin) &
        (Event.fecha <= range_end) 
        )
    rows = db(query).select(Process.nombre, Process.num_convocatoria, Process.entidad,
        Process.moneda, Process.monto, Process.enlace, Process.sintesis,
        Event.tipo, Event.hito, Event.fecha,
        orderby=Event.fecha|~Process.monto|Event.id)
    context = dict(rows=rows, u=u)
    message = response.render('seace/email_nearby_milestones.html', context)
    mail.send(to=['rcardenas@dynamo.pe'],
              subject="SEACE: hitos cercanos siendo " + datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
              message=message)


#            row.update_record(status='sent')
#        db.commit()
#    time.sleep(60) # check every minute
